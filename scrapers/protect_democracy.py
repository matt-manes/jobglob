from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import RecruiteeGruel
from gruel import ParsableItem
import models
from bs4 import Tag


class JobScraper(RecruiteeGruel):
    def parse_item(self, item: ParsableItem) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            a = item.find("a")
            assert isinstance(a, Tag)
            listing.position = a.text
            listing.url = f"{self.board.url}{a.get('href')}"
            listing.location = "Remote"
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None
