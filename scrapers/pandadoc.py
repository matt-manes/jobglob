from bs4 import Tag
from pathier import Pathier


root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import GreenhouseGruel
import models


class JobScraper(GreenhouseGruel):
    def parse_item(self, item: Tag) -> models.Listing | None:
        listing = super().parse_item(item)
        if listing and listing.url.strip("/") not in self.existing_listing_urls:
            listing.resolve_url()
        return listing
