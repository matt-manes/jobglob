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
        return soup.find_all("div", class_="position")

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            h2 = item.find("h2")
            assert isinstance(h2, Tag)
            listing.position = h2.text
            listing.location = "Remote"
            a = item.find("a")
            assert isinstance(a, Tag)
            listing.url = f"https://ridewithgps.com{a.get('href')}"
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None
