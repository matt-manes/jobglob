from typing import Any

from pathier import Pathier
from typing_extensions import override

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
import models
from jobgruel import WorkableGruel


class JobScraper(WorkableGruel):
    @override
    def parse_item(self, item: dict[str, Any]) -> models.Listing | None:
        listing = self.new_listing()
        listing.url = f"https://apply.workable.com/multimediallc/j/{item['shortcode']}"
        location = ""
        if item["remote"]:
            location += f"Remote {item['location']['country']}"
        else:
            location += f"{item['location']['city']}, {item['location']['country']}"
        listing.location = location
        listing.position = item["title"]
        return listing
