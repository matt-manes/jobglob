from typing import Any
from bs4 import Tag
from gruel import Gruel, ParsableItem
from gruel.gruel import ParsableItem
from seleniumuser import User

from jobbased import JobBased


class JobGruel(Gruel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with JobBased() as db:
            self.url = db.get_scrapable_board_url(self.name)
            self.company = db.get_scrapable_board_company(self.name)

    def store_item(self, item: dict):
        with JobBased() as db:
            if item["url"] not in db.scraped_listings_urls:
                db.add_scraped_listing(
                    item["position"], item["location"], item["url"], self.company
                )
                self.success_count += 1


class GreenhouseGruel(JobGruel):
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


class LeverGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.url)
        return soup.find_all("div", class_="posting")

    def parse_item(self, item: Tag) -> dict | None:
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


class BambooGruel(JobGruel):
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


class AshbyGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        with User(True) as user:
            user.get(self.url)
            soup = user.get_soup()
        sections = soup.find_all("div", class_="ashby-job-posting-brief-list")
        # assert isinstance(sections, Tag)
        items = []
        for section in sections:
            items.extend(section.find_all("a"))
        return items

    def parse_item(self, item: ParsableItem) -> dict | None:
        try:
            data = {}
            assert isinstance(item, Tag)
            data["url"] = f"https://jobs.ashbyhq.com{item.get('href')}"
            position = item.find("h3")
            assert isinstance(position, Tag)
            data["position"] = position.text
            location = item.find("p")
            assert isinstance(location, Tag)
            data["location"] = location.text.split("•")[1].strip()
            return data
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class WorkableGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        return self.get_page(
            f"https://apply.workable.com/api/v3/accounts/{self.url[self.url.rfind('/')+1:]}/jobs",
            "post",
        ).json()["results"]

    def parse_item(self, item: dict) -> dict | None:
        try:
            data = {}
            data[
                "url"
            ] = f"https://apply.workable.com/{self.company.lower().replace(' ','-')}/j/{item['shortcode']}"
            location = ""
            if item["remote"]:
                location += f"Remote {item['location']['country']}"
            else:
                location += f"{item['location']['city']}, {item['location']['country']}"
            data["location"] = location
            data["position"] = item["title"]
            return data
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class EasyApplyGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.url)
        listings = soup.find("div", attrs={"id": "list"})
        assert isinstance(listings, Tag)
        return listings.find_all("a", attrs={"target": "_blank"})

    def parse_item(self, item: ParsableItem) -> dict | None:
        try:
            data = {}
            assert isinstance(item, Tag)
            data["url"] = item.get("href")
            position = item.find("div", class_="no_word_break")
            assert isinstance(position, Tag)
            position = position.find("span")
            assert isinstance(position, Tag)
            data["position"] = position.text
            location = item.find("p")
            assert isinstance(location, Tag)
            location = location.find("span")
            assert isinstance(location, Tag)
            data["location"] = location.text
            return data
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class JobviteGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.url)
        job_tables = soup.find_all("table", class_="jv-job-list")
        listings = []
        for table in job_tables:
            if isinstance(table, Tag):
                listings.extend(table.find_all("tr"))
        return listings

    def parse_item(self, item: ParsableItem) -> dict | None:
        try:
            data = {}
            assert isinstance(item, Tag)
            a = item.find("a")
            assert isinstance(a, Tag)
            data["url"] = f"https://jobs.jobvite.com/careers{a.get('href')}"
            data["position"] = a.text
            td = item.find("td", class_="jv-job-list-location")
            assert isinstance(td, Tag)
            data["location"] = td.text
            return data
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class ApplyToJobGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.url)
        list_group = soup.find("ul", class_="list-group")
        if isinstance(list_group, Tag):
            return list_group.find_all("li", class_="list-group-item")
        return []

    def parse_item(self, item: ParsableItem) -> dict | None:
        try:
            data = {}
            assert isinstance(item, Tag)
            a = item.find("a")
            assert isinstance(a, Tag)
            data["url"] = a.get("href")
            data["position"] = a.text
            li = item.find("li")
            assert isinstance(li, Tag)
            data["location"] = li.text
            return data
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None
