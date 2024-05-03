import gruel
from bs4 import Tag
from pathier import Pathier
from typing_extensions import override

root = Pathier(__file__).parent
(root.parent).add_to_PATH()

import models
from jobgruel import JobGruel


class JobScraper(JobGruel):
    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        return soup.find_all(
            "a", attrs={"target": "_blank", "rel": "noreferrer noopener"}
        )

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
        """Parse `item` and return parsed data.

        e.g.
        >>> try:
        >>>     parsed = {}
        >>>     parsed["thing1"] = item["element"].split()[0]
        >>>     self.successes += 1
        >>>     return parsed
        >>> except Exception:
        >>>     self.logger.exception("message")
        >>>     self.failures += 1
        >>>     return None"""
        listing = self.new_listing()
        assert isinstance(item, Tag)
        listing.position = item.text
        listing.location = "remote"
        url = item.get("href")
        assert isinstance(url, str)
        listing.url = url
        return listing
