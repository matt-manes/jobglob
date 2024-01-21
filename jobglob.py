from datetime import datetime

import quickpool
from gruel import Brewer, GruelFinder
from noiftimer import Timer
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
        """Returns listing positions grouped by company."""
        grouped_listings = {}
        for listing in listings:
            if listing.company.name not in grouped_listings:
                grouped_listings[listing.company.name] = [listing.position]
            else:
                grouped_listings[listing.company.name].append(listing.position)
        return grouped_listings

    def print_new_listings(self):
        """Print listings added to the database since the start of the last scrape."""
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
        """Print and log scrapers that had errors grouped by error type."""
        errors = helpers.get_scrapers_with_errors(self.start_time)
        for error, names in errors.items():
            if names:
                message = f"{error}:\n"
                message += "\n".join(f"  {name}" for name in names)
                if error == "no_listings":
                    self.logger.info(message)
                else:
                    self.logger.logprint(message)
                    print()

    def postscrape_chores(self):
        self.print_new_listings()
        self.logprint_errors()
        super().postscrape_chores()
        print(
            f"Total runtime: {Timer.format_time((datetime.now() - self.start_time).total_seconds())}"
        )

    def scrape(self):
        with JobBased() as db:
            listings = db.get_listings()
        execute = lambda scraper: scraper(listings).scrape()
        pool = quickpool.ThreadPool(
            [execute] * len(self.scrapers), [(scraper,) for scraper in self.scrapers]
        )
        pool.execute()


def get_inactive_scrapers() -> list[str]:
    """Return a list of scrapers marked `inactive` in the database."""
    with JobBased() as db:
        boards = db.get_inactive_boards()
    return [helpers.name_to_stem(board.company.name) for board in boards]


def main():
    finder = GruelFinder(
        ["JobScraper"],
        ["*template.py"] + [f"*{name}.py" for name in get_inactive_scrapers()],
        root / "scrapers",
    )
    scrapers = finder.find()
    jobglob = JobGlob(scrapers)
    jobglob.brew()


if __name__ == "__main__":
    main()
