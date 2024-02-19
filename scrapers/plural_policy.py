from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from typing import Any

from bs4 import Tag

import models
from jobgruel import JobGruel


class JobScraper(JobGruel):
    def get_parsable_items(self) -> list[Tag]:
        soup = self.get_soup(self.board.url)
        return soup.find_all(
            "a", attrs={"target": "_blank", "rel": "noreferrer noopener"}
        )

    def parse_item(self, item: Tag) -> models.Listing | None:
        """Parse `item` and return parsed data.

        e.g.
        >>> try:
        >>>     parsed = {}
        >>>     parsed["thing1"] = item["element"].split()[0]
        >>>     self.successes += 1
        >>>     return parsed
        >>> except Exception:
        >>>     self.logger.exception("message")
        >>>     self.failures += 1
        >>>     return None"""
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            listing.position = item.text
            listing.location = "remote"
            url = item.get("href")
            assert isinstance(url, str)
            listing.url = url
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


if __name__ == "__main__":
    from datetime import datetime, timedelta

    import logglob

    start = datetime.now() - timedelta(seconds=2)
    j = JobScraper()
    j.scrape()
    print(logglob.load_log(j.board.company.name).filter_dates(start))
