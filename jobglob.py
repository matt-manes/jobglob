from datetime import datetime

from gruel.brewer import Brewer
from pathier import Pathier

import helpers
import models
from jobbased import JobBased

root = Pathier(__file__).parent


class JobGlob(Brewer):
    def prescrape_chores(self):
        with JobBased() as db:
            self.num_listings = db.count("listings")
        self.start_time = datetime.now()

    def group_by_company(self, listings: list[models.Listing]) -> dict[str, list[str]]:
        grouped_listings = {}
        for listing in listings:
            if listing.company.name not in grouped_listings:
                grouped_listings[listing.company.name] = [listing.position]
            else:
                grouped_listings[listing.company.name].append(listing.position)
        return grouped_listings

    def print_new_listings(self):
        with JobBased() as db:
            new_listings = db._get_listings(
                where=f"listings.date_added >= '{self.start_time}'"
            )
            num_new_listings = len(new_listings)
            self.logger.info(f"Added {num_new_listings} new listings")
        if num_new_listings > 0:
            grouped_listings = self.group_by_company(new_listings)
            print(f"Added {num_new_listings} new listings to the database:")
            for company, listings in grouped_listings.items():
                print(f"  {company}:")
                for listing in listings:
                    print(f"    {listing}")
        else:
            print("No new listings found.")
        print()

    def logprint_errors(self):
        errors = helpers.get_scrapers_with_errors(self.start_time)
        for error, names in errors.items():
            if names:
                message = f"{error}:\n"
                message += "\n".join(f"  {name}" for name in names)
                if error == "no_listings":
                    self.logger.info(message)
                else:
                    self.logprint(message)
                    print()

    def postscrape_chores(self):
        super().postscrape_chores()
        self.print_new_listings()
        self.logprint_errors()


if __name__ == "__main__":
    jobglob = JobGlob(
        ["JobScraper"],
        ["*template.py"],
        root / "scrapers",
    )
    jobglob.brew()
