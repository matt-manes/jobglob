import time

from bs4 import Tag
from gruel.gruel import ParsableItem
from pathier import Pathier
from seleniumuser import User

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
import models
from jobgruel import JobGruel


class JobScraper(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        with User(True) as user:
            user.get(self.board.url)
            time.sleep(1)
            soup = user.get_soup()
        return soup.find_all("div", class_="opportunity")

    def parse_item(self, item: Tag) -> models.Listing | None:
        url = "https://adhoc.rec.pro.ukg.net"
        try:
            listing = self.new_listing()
            a = item.find("a", attrs={"data-automation": "job-title"})
            assert isinstance(a, Tag)
            listing.url = f"{url}{a.get('href')}"
            listing.position = a.text
            span = item.find(
                "span", attrs={"data-automation": "city-state-zip-country-label"}
            )
            assert isinstance(span, Tag)
            listing.location = span.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None
