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
        return [
            tag.find("a")
            for tag in soup.find_all("p", class_="has-text-align-center")
            if tag.find("a")
        ]

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
        listing = self.new_listing()
        assert isinstance(item, Tag)
        listing.position = item.text
        listing.location = "remote"
        url = item.get("href")
        assert isinstance(url, str)
        listing.url = url
        return listing
