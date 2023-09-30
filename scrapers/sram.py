from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import JobGruel, ParsableItem
from typing import Any
from bs4 import Tag


class JobScraper(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.url)
        return soup.find_all("div", class_="job-listing-item")

    def parse_item(self, item: ParsableItem) -> dict | None:
        try:
            data = {}
            assert isinstance(item, Tag)
            a = item.find("a")
            assert isinstance(a, Tag)
            data["url"] = f"https://www.sram.com{a.get('href')}"
            data["position"] = a.get("title")
            p = item.find("p", class_="job-listing-item-loc")
            assert isinstance(p, Tag)
            data["location"] = p.text
            return data
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


if __name__ == "__main__":
    scraper = JobScraper()
    scraper.scrape()
