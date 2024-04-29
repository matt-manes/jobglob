from bs4 import Tag
from pathier import Pathier
from typing_extensions import override

import models

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
import jobgruel


class JobScraper(jobgruel.GreenhouseGruel):
    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
        listing = super().parse_item(item)
        if listing:
            listing.url = listing.url.replace("work-with-us", "work-with-us/apply")
        return listing
