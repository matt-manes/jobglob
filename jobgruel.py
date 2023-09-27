from typing import Any

from gruel import Gruel, ParsableItem
from bs4 import BeautifulSoup, Tag
from gruel.gruel import ParsableItem
from jobbased import JobBased
from pathier import Pathier
import inspect


class Jobgruel(Gruel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with JobBased() as db:
            self.url = db.get_scrapable_board_url(self.name)
            self.company = db.get_scrapable_board_company(self.name)

    def store_item(self, item: Any):
        with JobBased() as db:
            if item["url"] not in db.scraped_listings_urls:
                db.add_scraped_listing(
                    item["position"], item["location"], item["url"], self.company
                )
                self.success_count += 1


class Greenhousegruel(Jobgruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.url)
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


class Levergruel(Jobgruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.url)
        return soup.find_all("div", class_="posting")

    def parse_item(self, item: Tag) -> Any:
        try:
            data = {}
            title_element = item.find("a", class_="posting-title")
            assert isinstance(title_element, Tag)
            data["url"] = title_element.get("href")
            position = title_element.find("h5")
            assert isinstance(position, Tag)
            data["position"] = position.text
            location = title_element.find(
                "span",
                class_="sort-by-location posting-category small-category-label location",
            )
            assert isinstance(location, Tag)
            data["location"] = location.text
            return data
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class Bamboogruel(Jobgruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        return self.get_page(f"{self.url}/list").json()["result"]

    def parse_item(self, item: dict) -> dict | None:
        try:
            data = {}
            data["url"] = f"{self.url}/{item['id']}"
            city = item["location"].get("city", "")
            state = item["location"].get("state", "")
            remote = "Remote" if item["isRemote"] else ""
            data["location"] = ", ".join(
                detail for detail in [remote, city, state] if detail
            )
            data["position"] = item["jobOpeningName"]
            return data
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None
