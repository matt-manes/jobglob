from bs4 import Tag
from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import GreenhouseGruel
import models


class JobScraper(GreenhouseGruel):
    def parse_item(self, item: Tag) -> models.Listing | None:
        listing = super().parse_item(item)
        if listing:
            url = listing.url
            url = url[: url.rfind("?gh")]
            job_id = url[url.find("?") + 1 :]
            listing.url = f"https://verily.com/about-us/careers/open-roles?{job_id}"
        return listing
