import json
import math
import time
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag
from gruel import Gruel, ParsableItem
from pathier import Pathier, Pathish
from seleniumuser import User

import helpers
import models
from config import Config
from jobbased import JobBased

root = Pathier(__file__).parent

config = Config.load()
""" Subclasses of `Gruel` scraper engine.

`JobGruel` is the primary subclass.

The rest are subclasses of `JobGruel` for specific job boards like Greenhouse, Lever, BambooHR etc.
"""


class JobGruel(Gruel):
    """Primary job board scraping engine.

    Classes inheriting from `JobGruel` must implement:

    >>> get_parsable_items(self) -> list[ParsableItem]

    and

    >>> parse_item(self, item: ParsableItem) -> models.Listing | None

    To ensure proper loading, a subclass name should match the name of the board in `board_meta.toml`,
    but with the first letter capitalized and prepended to 'Gruel'.

    e.g. For 'greenhouse.io' boards: `class GreenhouseGruel(JobGruel):`"""

    def __init__(
        self,
        existing_listings: list[models.Listing] | None = None,
        company_stem: str | None = None,  # don't need this if `board` is provided
        board: models.Board | None = None,
    ):
        super().__init__(
            helpers.name_to_stem(board.company.name) if board else company_stem,
            log_dir=config.scraper_logs_dir,
        )
        # database connection only gets opened if `get_board` or `_get_listings` is called
        db = JobBased(commit_on_close=False)
        self.board = board or db.get_board(self.name)
        listings = (
            [
                listing
                for listing in existing_listings
                if listing.company.id_ == self.board.company.id_
            ]
            if existing_listings
            else db._get_listings(f"listings.company_id = {self.board.company.id_}")
        )
        db.close()
        self.existing_listings = listings
        self.existing_listing_urls = [listing.url for listing in listings]
        self.already_added_listings = 0
        # self.found_listings: list[models.Listing] = []

    @property
    def had_failures(self) -> bool:
        """`True` if getting parsable items, parsing items, or unexpected failures occured."""
        return (
            (self.fail_count > 0)
            or self.failed_to_get_parsable_items
            or self.unexpected_failure_occured
        )

    def request(
        self, url: str, method: str = "get", headers: dict[str, str] = {}
    ) -> requests.Response:
        """Returns a `request.Response` object for the given `url`.

        The underlying base class (`Gruel`) uses a randomized `User-Agent` if one is not provided in `headers`.

        Logs the response status code and the resolved url if different from the provided `url`.
        """
        response = super().request(url, method, headers)
        if response.status_code == 404:
            self.logger.error(f"{url} returned status code 404")
        else:
            self.logger.info(f"{url} returned status code {response.status_code}")
        if url == self.board.url and url != response.url.strip("/"):
            self.logger.warning(f"Board url '{url}' resolved to '{response.url}'")
        return response

    def new_listing(self) -> models.Listing:
        """Returns a `models.Listing` object that is only populated with this scraper's company model."""
        return models.Listing(self.board.company)

    def store_item(self, listing: models.Listing):
        """Add `listing` to the database if it doesn't already exist (based off `listing.url`)."""
        listing.url = listing.url.strip("/")
        if listing.url not in self.existing_listing_urls:
            with JobBased() as db:
                listing.date_added = datetime.now()
                listing.prune_strings()
                try:
                    db.add_listing(listing)
                    self.success_count += 1
                except Exception as e:
                    if "UNIQUE constraint failed" not in str(e):
                        self.logger.exception("Error adding listing")
                        self.fail_count += 1
                    else:
                        self.already_added_listings += 1

    def mark_dead_listings(self):
        """Mark listings from the database as dead if they aren't found in the scraped listings."""
        num_dead = 0
        # Don't mark listings dead if scraper had a parse fail
        if self.parsed_items and not self.had_failures:
            self.logger.info("Checking for dead listings.")
            found_urls = [listing.url for listing in self.parsed_items]
            live_listings = [
                listing for listing in self.existing_listings if listing.alive
            ]
            dead_listings = [
                listing for listing in live_listings if listing.url not in found_urls
            ]
            num_dead = len(dead_listings)
            if dead_listings:
                with JobBased() as db:
                    for listing in dead_listings:
                        db.mark_dead(listing.id_)
                        self.logger.info(
                            f"Marking listing with id {listing.id_} as dead. ({listing.position} - {listing.url})"
                        )
        self.logger.info(f"Marked {num_dead} listings as dead.")

    def mark_resurrected_listings(self):
        """Reset the alive status of a listing if the scraper found it and it was previously marked dead."""
        num_resurrected = 0
        found_urls = [listing.url for listing in self.parsed_items]
        dead_listings = [
            listing for listing in self.existing_listings if not listing.alive
        ]
        resurrected_listings = [
            listing for listing in dead_listings if listing.url in found_urls
        ]
        num_resurrected = len(resurrected_listings)
        if resurrected_listings:
            with JobBased() as db:
                for listing in resurrected_listings:
                    db.reset_alive_status(listing.id_)
                    db.delete("seen_listings", f"listing_id = {listing.id_}")
                    self.logger.info(
                        f"Resurrecting listing with id {listing.id_}. ({listing.position} - {listing.url})"
                    )
        self.logger.info(f"Resurrected {num_resurrected} listings.")

    def postscrape_chores(self):
        self.mark_dead_listings()
        self.mark_resurrected_listings()
        super().postscrape_chores()


class GreenhouseGruel(JobGruel):
    """`JobGruel` subclass for Greenhouse job boards."""

    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.board.url)
        return soup.find_all("div", class_="opening")

    def parse_item(self, item: Tag) -> models.Listing | None:
        try:
            listing = self.new_listing()
            element = item.find("a")
            assert isinstance(element, Tag)
            listing.position = element.text
            href = element.get("href")
            assert isinstance(href, str)
            if href.startswith("http"):
                listing.url = href.replace("http://", "https://", 1)
            else:
                listing.url = "https://boards.greenhouse.io" + href
            span = item.find("span")
            if isinstance(span, Tag):
                listing.location = span.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class LeverGruel(JobGruel):
    """`JobGruel` subclass for Lever job boards."""

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
            if isinstance(location, Tag):
                listing.location = location.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class BambooGruel(JobGruel):
    """`JobGruel` subclass for BambooHR job boards."""

    def get_parsable_items(self) -> list[ParsableItem]:
        return self.request(f"{self.board.url}/list").json()["result"]

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
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class AshbyGruel(JobGruel):
    """`JobGruel` subclass for Ashby job boards.

    Requires Firefox and Geckodriver."""

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
            if isinstance(location, Tag):
                listing.location = location.text.split("•")[1].strip()
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class WorkableGruel(JobGruel):
    """`JobGruel` subclass for Workable job boards."""

    def get_parsable_items(self) -> list[ParsableItem]:
        return self.request(
            f"https://apply.workable.com/api/v3/accounts/{self.board.url[self.board.url.rfind('/')+1:]}/jobs",
            "post",
        ).json()["results"]

    def parse_item(self, item: dict) -> models.Listing | None:
        try:
            listing = self.new_listing()
            listing.url = f"https://apply.workable.com/{self.board.url[self.board.url.rfind('/')+1:]}/j/{item['shortcode']}"
            location = ""
            if item["remote"]:
                location += f"Remote {item['location']['country']}"
            else:
                location += f"{item['location']['city']}, {item['location']['country']}"
            listing.location = location
            listing.position = item["title"]
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class EasyapplyGruel(JobGruel):
    """`JobGruel` subclass for Easyapply job boards."""

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
            if isinstance(location, Tag):
                location = location.find("span")
                assert isinstance(location, Tag)
                listing.location = location.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class JobviteGruel(JobGruel):
    """`JobGruel` subclass for Jobvite job boards."""

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
            if isinstance(td, Tag):
                listing.location = td.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class ApplytojobGruel(JobGruel):
    """`JobGruel` subclass for ApplyToJob job boards."""

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
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class SmartrecruiterGruel(JobGruel):
    """`JobGruel` subclass for SmartRecruiters job boards."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company_page = self.board.url[self.board.url.rfind("/") + 1 :]
        self.api_endpoint = (
            f"https://careers.smartrecruiters.com/{company_page}/api/more?page="
        )

    def get_parsable_items(self) -> list[ParsableItem]:
        page_count = 0
        listings = []
        while True:
            if page_count == 0:
                soup = self.get_soup(self.board.url)
                listings.extend(soup.find_all("a", class_="link--block details"))
            else:
                response = self.request(f"{self.api_endpoint}{page_count}")
                if not response.text:
                    break
                elif response.status_code == 404:
                    raise RuntimeError("Smart recruiters api endpoint returning 404.")
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
            if isinstance(li, Tag):
                listing.location = li.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class RecruiteeGruel(JobGruel):
    """`JobGruel` subclass for Recruitee job boards."""

    def get_parsable_items(self) -> list[ParsableItem]:
        soup = self.get_soup(self.board.url)
        output = soup.find("output")
        if not isinstance(output, Tag):
            return []
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
            if isinstance(city, Tag):
                country = item.find("span", class_=f"{css}country")
                assert isinstance(country, Tag)
                listing.location = f"{city.text}, {country.text}"
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class RecruiteeAltGruel(JobGruel):
    """Alternative `JobGruel` subclass for Recruitee job boards."""

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
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class BreezyGruel(JobGruel):
    """`JobGruel` subclass for Breezy job boards."""

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
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class MyworkdayGruel(JobGruel):
    """`JobGruel` subclass for MyWorkDay job boards."""

    def get_num_pages(self, user: User) -> int:
        num_pages = None
        attempts = 0
        max_attempts = 10
        jobs_per_page = 20
        soup = user.get_soup()
        while num_pages is None and attempts < max_attempts:
            try:
                p = soup.find("p", attrs={"data-automation-id": "jobFoundText"})
                assert isinstance(p, Tag)
                num_jobs = int(p.text.split()[0])
                num_pages = math.ceil(num_jobs / jobs_per_page)
            except Exception as e:
                time.sleep(1)
                soup = user.get_soup()
            finally:
                attempts += 1
        if not num_pages:
            raise RuntimeError("Could not get num_pages")
        return num_pages

    def get_parsable_items(self) -> list[ParsableItem]:
        with User(True) as user:
            user.get(self.board.url)
            time.sleep(1)
            num_pages = self.get_num_pages(user)
            soup = user.get_soup()
            listings = []
            for page in range(1, num_pages + 1):
                if page > 1:
                    user.click("//button[@data-uxi-element-id='next']")
                    time.sleep(1)
                    soup = user.get_soup()
                job_list = soup.find("ul", attrs={"role": "list"})
                assert isinstance(job_list, Tag)
                listings.extend(
                    [
                        listing
                        for listing in job_list.find_all("li", recursive=False)
                        if listing.find("div", class_="css-qiqmbt")
                    ]
                )
        return listings

    def parse_item(self, item: ParsableItem) -> models.Listing | None:
        try:
            listing = self.new_listing()
            assert isinstance(item, Tag)
            a = item.find("a", attrs={"data-automation-id": "jobTitle"})
            assert isinstance(a, Tag)
            url = self.board.url[
                : self.board.url.rfind("/")
                if self.board.url.endswith("careers")
                else self.board.url.find("/", self.board.url.find(".com"))
            ]
            listing.url = f"{url}{a.get('href')}"
            listing.position = a.text
            dl = item.find("dl")
            if isinstance(dl, Tag):
                listing.location = dl.text.lstrip("locations")
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class TeamtailorGruel(JobGruel):
    """`JobGruel` subclass for TeamTailor job boards."""

    def get_parsable_items(self) -> list[Tag]:
        soup = self.get_soup(self.board.url)
        job_container = soup.find("ul", attrs={"id": "jobs_list_container"})
        assert isinstance(job_container, Tag)
        return job_container.find_all("li")

    def parse_item(self, item: Tag) -> models.Listing | None:
        try:
            listing = self.new_listing()
            a = item.find("a")
            assert isinstance(a, Tag)
            listing.url = str(a.get("href"))
            position_span = a.find("span")
            assert isinstance(position_span, Tag)
            listing.position = position_span.text
            deet_div = a.find("div", class_="mt-1 text-md")
            assert isinstance(deet_div, Tag)
            listing.location = deet_div.text
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class PaycomGruel(JobGruel):
    """`JobGruel` subclass for Paycom job boards."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://www.paycomonline.net"

    def get_parsable_items(self) -> list[dict]:
        soup = self.get_soup(self.board.url)
        main_content = soup.find("div", attrs={"id": "main-content"})
        assert isinstance(main_content, Tag)
        data_script = main_content.find_all("script")[0].text.strip()
        data_script = data_script[data_script.find("[") - 1 : data_script.rfind(";")]
        data = json.loads(data_script)
        return data

    def parse_item(self, item: dict) -> models.Listing | None:
        try:
            listing = self.new_listing()
            listing.position = item["title"]
            listing.location = item["location"]["description"]
            listing.url = f"{self.base_url}{item['url']}"
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class PaylocityGruel(JobGruel):
    """`JobGruel` subclass for Paylocity job boards."""

    def get_parsable_items(self) -> list[dict]:
        soup = self.get_soup(self.board.url)
        # Look for `<script> window.pageData = `
        for script in soup.find_all("script"):
            text = self.clean_string(script.text)
            if text.startswith("window.pageData "):
                text = text[text.find("{") : text.rfind(";")]
                return json.loads(text)["Jobs"]
        raise RuntimeError("Could not find `window.pageData` script.")

    def parse_item(self, item: dict) -> models.Listing | None:
        try:
            listing = self.new_listing()
            listing.position = item["JobTitle"]
            listing.location = item["LocationName"]
            listing.url = f"https://recruiting.paylocity.com/Recruiting/Jobs/Details/{item['JobId']}"
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class DoverGruel(JobGruel):
    """`JobGruel` subclass for Dover job boards."""

    def get_parsable_items(self) -> list[dict]:
        # https://app.dover.io/{company}/careers/{board_id}
        board_id = self.board.url[self.board.url.rfind("/") + 1 :]
        url = f"https://app.dover.io/api/v1/careers-page/{board_id}/jobs"
        return self.request(url).json()["results"]

    def parse_item(self, item: dict) -> models.Listing | None:
        try:
            listing = self.new_listing()
            listing.position = item["title"]
            if item["locations"]:
                listing.location = "\n".join(
                    location["name"] for location in item["locations"]
                )
            anchor = ".io/"
            company = self.board.url[
                self.board.url.find(anchor)
                + len(anchor) : self.board.url.find("/careers/")
            ]
            listing.url = f"https://app.dover.io/apply/{company}/{item['id']}"
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None


class RipplingGruel(JobGruel):
    """`JobGruel` subclass for Rippling job boards."""

    def get_parsable_items(self) -> list[Tag]:
        soup = self.get_soup(self.board.url)
        return soup.find_all("div", class_="css-cq05mv")

    def parse_item(self, item: Tag) -> models.Listing | None:
        try:
            listing = self.new_listing()
            a = item.find("a")
            assert isinstance(a, Tag)
            listing.position = a.text
            url = a.get("href")
            assert isinstance(url, str)
            listing.url = url
            div = item.find("div", class_="css-mwvv03")
            assert isinstance(div, Tag)
            for subdiv in div.find_all("div"):
                if subdiv.find("span", attrs={"data-icon": "LOCATION_OUTLINE"}):
                    p = subdiv.find("p")
                    assert isinstance(p, Tag)
                    listing.location = p.text
                    break
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None
