import gruel
from bs4 import Tag
from pathier import Pathier
from typing_extensions import override

root = Pathier(__file__).parent
(root.parent).add_to_PATH()

import models
from jobgruel import RecruiteeGruel


class JobScraper(RecruiteeGruel):
    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
        listing = self.new_listing()
        assert isinstance(item, Tag)
        a = item.find("a")
        assert isinstance(a, Tag)
        listing.position = a.text
        listing.url = f"{self.board.url}{a.get('href')}"
        listing.location = "Remote"
        return listing
