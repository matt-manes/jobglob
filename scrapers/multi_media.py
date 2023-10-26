from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import WorkableGruel
import models


class JobScraper(WorkableGruel):
    def parse_item(self, item: dict) -> models.Listing | None:
        try:
            listing = self.new_listing()
            listing.url = (
                f"https://apply.workable.com/multimediallc/j/{item['shortcode']}"
            )
            location = ""
            if item["remote"]:
                location += f"Remote {item['location']['country']}"
            else:
                location += f"{item['location']['city']}, {item['location']['country']}"
            listing.location = location
            listing.position = item["title"]
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None
