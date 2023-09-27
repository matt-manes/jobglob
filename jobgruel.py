from typing import Any

from gruel import Gruel, ParsableItem
from bs4 import BeautifulSoup, Tag
from jobbased import JobBased
from pathier import Pathier
import inspect


class Jobgruel(Gruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        """Get relevant webpages and extract raw data that needs to be parsed.

        e.g. first 10 results for an endpoint that returns json content
        >>> return self.get_page(some_url).json()[:10]"""
        raise NotImplementedError

    def parse_item(self, item: ParsableItem) -> Any:
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

    def store_item(self, item: Any):
        """Store `item`."""
        raise NotImplementedError


class Greenhousegruel(Jobgruel):
    @property
    def name(self) -> str:
        return Pathier(inspect.getsourcefile(type(self))).stem  # type: ignore

    def get_parsable_items(self) -> list[ParsableItem]:
        with JobBased() as db:
            url = db.get_scrapable_board_url(self.name)
        soup = self.get_soup(url)
        return soup.find_all("div", class_="opening")

    def parse_item(self, item: Tag) -> dict | None:
        try:
            data = {}
            element = item.find("a")
            assert isinstance(element, Tag)
            href = element.get("href")
            assert isinstance(href, str)
            data["url"] = "https://boards.greenhouse.io" + href
            data["position"] = element.text
            span = item.find("span")
            assert isinstance(span, Tag)
            data["location"] = span.text
            return data
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None

    def store_item(self, item: dict):
        with JobBased() as db:
            if item["url"] not in db.scraped_listings_urls:
                db.add_scraped_listing(
                    item["position"], item["location"], item["url"], "Strava"
                )
                self.success_count += 1
