from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from typing import Any

from bs4 import Tag

import models
from jobgruel import JobGruel, ParsableItem


class JobScraper(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        """Get relevant webpages and extract raw data that needs to be parsed.

        e.g. first 10 results for an endpoint that returns json content
        >>> return self.get_page(some_url).json()[:10]"""
        raise NotImplementedError

    def parse_item(self, item: ParsableItem) -> models.Listing | None:
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
        raise NotImplementedError


if __name__ == "__main__":
    from datetime import datetime, timedelta

    import helpers

    start = datetime.now() - timedelta(seconds=2)
    j = JobScraper()
    j.scrape()
    print(helpers.load_log(j.board.company.name).filter_dates(start))
