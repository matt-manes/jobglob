from pathier import Pathier
from typing_extensions import override

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from typing import Any

from bs4 import Tag

import models
from jobgruel import JobGruel


class JobScraper(JobGruel):
    @override
    def get_parsable_items(self) -> list[Tag]:
        soup = self.get_soup(self.board.url)
        return soup.find_all("div", class_="job-listing-item")

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            a = item.find("a")
            assert isinstance(a, Tag)
            listing.url = f"https://www.sram.com{a.get('href')}"
            title = a.get("title")
            assert isinstance(title, str)
            listing.position = title
            p = item.find("p", class_="job-listing-item-loc")
            assert isinstance(p, Tag)
            listing.location = p.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


if __name__ == "__main__":
    scraper = JobScraper()
    scraper.scrape()
