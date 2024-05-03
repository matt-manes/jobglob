import gruel
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
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        job_positions = soup.find("div", attrs={"id": "job_positions"})
        assert isinstance(job_positions, Tag)
        return job_positions.find_all("div", class_="col-lg-3 col-md-6 post-column")

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
        listing = self.new_listing()
        a = item.find("a")
        assert isinstance(a, Tag)
        listing.position = a.text
        url = a.get("href")
        assert isinstance(url, str)
        listing.url = url
        return listing
