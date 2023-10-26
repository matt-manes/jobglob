from pathier import Pathier


root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import WorkableGruel
import models


class JobScraper(WorkableGruel):
    def parse_item(self, item: dict) -> models.Listing | None:
        listing = super().parse_item(item)
        if listing:
            listing.url = listing.url.replace("lmax-group", "lmax")
        return listing
