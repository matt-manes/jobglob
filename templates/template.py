import gruel
from bs4 import Tag
from pathier import Pathier
from typing_extensions import Any, override

root = Pathier(__file__).parent
(root.parent).add_to_PATH()

import models
from jobgruel import JobGruel


class JobScraper(JobGruel):
    @override
    def get_source(self) -> gruel.Response:
        raise NotImplementedError

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Any]:
        raise NotImplementedError

    @override
    def parse_item(self, item: Any) -> models.Listing | None:
        """Parse `item` into a `models.Listing` instance."""
        listing = self.new_listing()
        raise NotImplementedError


if __name__ == "__main__":
    from datetime import datetime, timedelta

    import logglob

    start = datetime.now() - timedelta(seconds=2)
    j = JobScraper()
    j.scrape()
    print(logglob.load_log(j.board.company.name).filter_dates(start))
