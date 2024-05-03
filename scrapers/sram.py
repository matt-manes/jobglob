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
        return soup.find_all("div", class_="job-listing-item")

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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
