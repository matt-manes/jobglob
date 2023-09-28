from gruel import Brewer
import logparse
from jobbased import JobBased
from pathier import Pathier

root = Pathier(__file__).parent


class JobGlob(Brewer):
    def prescrape_chores(self):
        with JobBased() as db:
            self.num_listings = db.count("scraped_listings")

    def postscrape_chores(self):
        with JobBased() as db:
            num_new_listings = db.count("scraped_listings") - self.num_listings
            scraped_companies = db.select(
                "companies",
                ["name"],
                [
                    "INNER JOIN scrapable_boards ON companies.board_id = scrapable_boards.board_id"
                ],
            )
        print(f"Added {num_new_listings} new listings to the database.")
        print()

        scrape_fails = logparse.get_failed_scrapers()
        if scrape_fails:
            print("Scrape failures:")
        for file in scrape_fails:
            print(f"  {file}")
            print()

        parse_fails = []
        for company in scraped_companies:
            name = company["name"]
            fails = logparse.get_parse_counts(name)
            if fails and fails[1] > 0:
                parse_fails.append(f"  {name}: {fails[1]} parsing failures")
        if parse_fails:
            print("Parsing failures:")
            print(*parse_fails, sep="\n")
            print()


if __name__ == "__main__":
    jobglob = JobGlob(["JobScraper"], ["*template.py"], root / "scrapers")
    jobglob.brew()
