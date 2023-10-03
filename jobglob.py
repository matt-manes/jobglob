from gruel import Brewer
import logparse
from jobbased import JobBased
from pathier import Pathier

root = Pathier(__file__).parent


class JobGlob(Brewer):
    def prescrape_chores(self):
        with JobBased() as db:
            self.num_listings = db.count("scraped_listings")

    def group_by_company(self, listings: list[dict[str, str]]) -> dict[str, list[str]]:
        grouped_listings = {}
        for listing in listings:
            if listing["company"] not in grouped_listings:
                grouped_listings[listing["company"]] = [listing["position"]]
            else:
                grouped_listings[listing["company"]].append(listing["position"])
        return grouped_listings

    def postscrape_chores(self):
        with JobBased() as db:
            num_new_listings = db.count("scraped_listings") - self.num_listings
            new_listings = self.group_by_company(
                db.select(
                    "scraped_listings",
                    ["companies.name AS company", "position"],
                    [
                        "INNER JOIN companies ON scraped_listings.company_id = companies.company_id"
                    ],
                    order_by="scraped_listings.date_added DESC",
                    limit=num_new_listings,
                )
            )
            scraped_companies = list(new_listings.keys())

        print(f"Added {num_new_listings} new listings to the database:")
        for company, listings in new_listings.items():
            print(f"  {company}:")
            for listing in listings:
                print(f"    {listing}")
        print()

        scrape_fails = logparse.get_failed_scrapers()
        if scrape_fails:
            print("Scrape failures:")
        for file in scrape_fails:
            print(f"  {file}")
            print()

        parse_fails = []
        for company in scraped_companies:
            fails = logparse.get_parse_counts(company)
            if fails and fails[1] > 0:
                parse_fails.append(f"  {company}: {fails[1]} parsing failures")
        if parse_fails:
            print("Parsing failures:")
            print(*parse_fails, sep="\n")
            print()


if __name__ == "__main__":
    jobglob = JobGlob(["JobScraper"], ["*template.py"], root / "scrapers")
    jobglob.brew()
