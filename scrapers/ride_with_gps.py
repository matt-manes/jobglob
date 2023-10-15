from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import JobGruel, ParsableItem
from typing import Any
from bs4 import Tag


class JobScraper(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.url)
        return soup.find_all("div", class_="position")

    def parse_item(self, item: ParsableItem) -> dict | None:
        try:
            data = {}
            assert isinstance(item, Tag)
            h2 = item.find("h2")
            assert isinstance(h2, Tag)
            data["position"] = h2.text
            data["location"] = "Remote"
            a = item.find("a")
            assert isinstance(a, Tag)
            data["url"] = f"https://ridewithgps.com{a.get('href')}"
            return data
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None
