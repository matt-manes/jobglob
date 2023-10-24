import time
from typing import Any

import requests
from bs4 import Tag
from gruel import Gruel, ParsableItem
from gruel.gruel import ParsableItem
from seleniumuser import User

import models
from jobbased import JobBased


class JobGruel(Gruel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with JobBased() as db:
            self.board = db.get_board(self.name)
            self.existing_listing_urls = [
                listing.url
                for listing in db._get_listings(
                    f"listings.company_id = {self.board.company.id_}"
                )
            ]
        self.already_added_listings = 0

    def get_page(
        self, url: str, method: str = "get", headers: dict[str, str] = {}
    ) -> requests.Response:
        response = super().get_page(url, method, headers)
        if response.status_code == 404:
            self.logger.error(f"{url} returned status code 404")
        else:
            self.logger.info(f"{url} returned status code {response.status_code}")
        if url == self.board.url and url != response.url.strip("/"):
            self.logger.warning(f"Board url '{url}' resolved to '{response}'")
        return response

    def new_listing(self) -> models.Listing:
        return models.Listing(self.board.company)

    def store_item(self, listing: models.Listing):
        if listing.url not in self.existing_listing_urls:
            with JobBased() as db:
                try:
                    db.add_listing(listing)
                    self.success_count += 1
                except Exception as e:
                    if "UNIQUE constraint failed" not in str(e):
                        self.logger.exception("Error adding listing")
                        self.fail_count += 1
                    else:
                        self.already_added_listings += 1


class GreenhouseGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.board.url)
        return soup.find_all("div", class_="opening")

    def parse_item(self, item: Tag) -> models.Listing | None:
        try:
            listing = self.new_listing()
            element = item.find("a")
            assert isinstance(element, Tag)
            href = element.get("href")
            assert isinstance(href, str)
            if "https" in href:
                listing.url = href
            else:
                listing.url = "https://boards.greenhouse.io" + href
            listing.position = element.text
            span = item.find("span")
            assert isinstance(span, Tag)
            listing.location = span.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class LeverGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.board.url)
        return soup.find_all("div", class_="posting")

    def parse_item(self, item: Tag) -> models.Listing | None:
        try:
            listing = self.new_listing()
            title_element = item.find("a", class_="posting-title")
            assert isinstance(title_element, Tag)
            url = title_element.get("href")
            assert isinstance(url, str)
            listing.url = url
            position = title_element.find("h5")
            assert isinstance(position, Tag)
            listing.position = position.text
            location = title_element.find(
                "span",
                class_="sort-by-location posting-category small-category-label location",
            )
            assert isinstance(location, Tag)
            listing.location = location.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class BambooGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        return self.get_page(f"{self.board.url}/list").json()["result"]

    def parse_item(self, item: dict) -> models.Listing | None:
        try:
            listing = self.new_listing()
            listing.url = f"{self.board.url}/{item['id']}"
            city = item["location"].get("city", "")
            state = item["location"].get("state", "")
            remote = "Remote" if item["isRemote"] else ""
            listing.location = ", ".join(
                detail for detail in [remote, city, state] if detail
            )
            listing.position = item["jobOpeningName"]
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class AshbyGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        with User(True) as user:
            user.get(self.board.url)
            time.sleep(1)
            soup = user.get_soup()
        sections = soup.find_all("div", class_="ashby-job-posting-brief-list")
        items = []
        for section in sections:
            items.extend(section.find_all("a"))
        return items

    def parse_item(self, item: ParsableItem) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            listing.url = f"https://jobs.ashbyhq.com{item.get('href')}"
            position = item.find("h3")
            assert isinstance(position, Tag)
            listing.position = position.text
            location = item.find("p")
            assert isinstance(location, Tag)
            listing.location = location.text.split("•")[1].strip()
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class WorkableGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        return self.get_page(
            f"https://apply.workable.com/api/v3/accounts/{self.board.url[self.board.url.rfind('/')+1:]}/jobs",
            "post",
        ).json()["results"]

    def parse_item(self, item: dict) -> models.Listing | None:
        try:
            listing = self.new_listing()
            listing.url = f"https://apply.workable.com/{self.board.company.name.lower().replace(' ','-')}/j/{item['shortcode']}"
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


class EasyapplyGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.board.url)
        listings = soup.find("div", attrs={"id": "list"})
        assert isinstance(listings, Tag)
        return listings.find_all("a", attrs={"target": "_blank"})

    def parse_item(self, item: ParsableItem) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            url = item.get("href")
            assert isinstance(url, str)
            listing.url = url
            position = item.find("div", class_="no_word_break")
            assert isinstance(position, Tag)
            position = position.find("span")
            assert isinstance(position, Tag)
            listing.position = position.text
            location = item.find("p")
            assert isinstance(location, Tag)
            location = location.find("span")
            assert isinstance(location, Tag)
            listing.location = location.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class JobviteGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.board.url)
        job_tables = soup.find_all("table", class_="jv-job-list")
        listings = []
        for table in job_tables:
            if isinstance(table, Tag):
                listings.extend(table.find_all("tr"))
        return listings

    def parse_item(self, item: ParsableItem) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            a = item.find("a")
            assert isinstance(a, Tag)
            listing.url = f"https://jobs.jobvite.com/careers{a.get('href')}"
            listing.position = a.text
            td = item.find("td", class_="jv-job-list-location")
            assert isinstance(td, Tag)
            listing.location = td.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class ApplytojobGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.board.url)
        list_group = soup.find("ul", class_="list-group")
        if isinstance(list_group, Tag):
            return list_group.find_all("li", class_="list-group-item")
        return []

    def parse_item(self, item: ParsableItem) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            a = item.find("a")
            assert isinstance(a, Tag)
            url = a.get("href")
            assert isinstance(url, str)
            listing.url = url
            listing.position = a.text
            li = item.find("li")
            assert isinstance(li, Tag)
            listing.location = li.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class SmartrecruiterGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        page_count = 0
        company_page = self.board.url[self.board.url.rfind("/") + 1 :]
        listings = []
        while True:
            if page_count == 0:
                soup = self.get_soup(self.board.url)
                listings.extend(soup.find_all("a", class_="link--block details"))
            else:
                response = self.get_page(
                    f"https://careers.smartrecruiters.com/{company_page}/api/more?page={page_count}"
                )
                if not response.text:
                    break
                soup = self.as_soup(response)
                listings.extend(soup.find_all("a", class_="link--block details"))
            page_count += 1
        return listings

    def parse_item(self, item: ParsableItem) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            url = item.get("href")
            assert isinstance(url, str)
            listing.url = url
            h4 = item.find("h4")
            assert isinstance(h4, Tag)
            listing.position = h4.text
            li = item.find("li", class_="job-desc")
            assert isinstance(li, Tag)
            listing.location = li.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class RecruiteeGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.board.url)
        output = soup.find("output")
        assert isinstance(output, Tag)
        div_grid = output.find("div")
        assert isinstance(div_grid, Tag)
        return div_grid.find_all("div", recursive=False)

    def parse_item(self, item: ParsableItem) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            a = item.find("a")
            assert isinstance(a, Tag)
            listing.position = a.text
            listing.url = f"{self.board.url}{a.get('href')}"
            css = "custom-css-style-job-location-"
            city = item.find("span", class_=f"{css}city")
            assert isinstance(city, Tag)
            country = item.find("span", class_=f"{css}country")
            assert isinstance(country, Tag)
            listing.location = f"{city}, {country}"
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class RecruiteeAltGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.board.url)
        return soup.find_all("div", class_="job")

    def parse_item(self, item: ParsableItem) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            a = item.find("a")
            assert isinstance(a, Tag)
            listing.position = a.text
            listing.url = f"{self.board.url}{a.get('href')}"
            li = item.find("li", class_="job-location")
            assert isinstance(li, Tag)
            listing.location = li.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None


class BreezyGruel(JobGruel):
    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.board.url)
        return soup.find_all("li", class_="position transition")

    def parse_item(self, item: ParsableItem) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            a = item.find("a")
            assert isinstance(a, Tag)
            listing.url = f"{self.board.url}{a.get('href')}"
            h2 = a.find("h2")
            assert isinstance(h2, Tag)
            listing.position = h2.text
            li = a.find("li", class_="location")
            assert isinstance(li, Tag)
            listing.location = li.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item")
            self.fail_count += 1
            return None
