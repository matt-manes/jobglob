import json
from datetime import datetime
from functools import cached_property

import gruel
from bs4 import ResultSet, Tag
from pathier import Pathier
from typing_extensions import Any, Callable, Sequence, override

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


class JobGruel(gruel.Gruel):
    """Primary job board scraping engine.

    Classes inheriting from `JobGruel` must implement:

    @override
    >>> get_source(self)->Response

    @override
    >>> get_parsable_items(self) -> list[Any]

    and

    @override
    >>> parse_item(self, item: Any) -> models.Listing | None

    To ensure proper loading, a subclass name should match the name of the board in `board_meta.toml`,
    but with the first letter capitalized and prepended to 'Gruel'.

    e.g. For 'greenhouse.io' boards: `class GreenhouseGruel(JobGruel):`"""

    @override
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
        # Not using context manager so database connection only gets opened if `get_board` or `_get_listings` is called
        db = JobBased(commit_on_close=False)
        self.board = board if board else db.get_board(self.name)
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
        self.new_listings = 0

    def new_listing(self) -> models.Listing:
        """Returns a `models.Listing` object that is only populated with this scraper's company model."""
        return models.Listing(self.board.company)

    @override
    def store_items(self, items: Sequence[models.Listing | None]):
        """Add listings to the database if it doesn't already exist (based off `listing.url`)."""
        for item in items:
            if not item:
                pass
            else:
                item.url = item.url.strip("/")
                if item.url not in self.existing_listing_urls:
                    with JobBased() as db:
                        item.date_added = datetime.now()
                        item.prune_strings()
                        try:
                            db.add_listing(item)
                            self.new_listings += 1
                        except Exception as e:
                            if "UNIQUE constraint failed" not in str(e):
                                self.logger.exception(
                                    "Error adding listing to database."
                                )
                            else:
                                self.already_added_listings += 1

    def mark_dead_listings(self):
        """Mark listings from the database as dead if they aren't found in the scraped listings."""
        num_dead = 0
        # Don't mark listings dead if scraper had a parse fail
        if self.parsed_items and not self.had_failures:
            self.logger.info("Checking for dead listings.")
            found_urls = [listing.url for listing in self.parsed_items if listing]
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
        found_urls = [listing.url for listing in self.parsed_items if listing]
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
                    db.resurrect_listing(listing.id_)
                    self.logger.info(
                        f"Resurrecting listing with id {listing.id_}. ({listing.position} - {listing.url})"
                    )
        self.logger.info(f"Resurrected {num_resurrected} listings.")

    @override
    def postscrape_chores(self):
        super().postscrape_chores()
        self.mark_dead_listings()
        self.mark_resurrected_listings()
        self.logger.info(f"Added {self.new_listings} new listings to the database.")


class GreenhouseGruel(JobGruel):
    """`JobGruel` subclass for Greenhouse job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        return soup.find_all("div", class_="opening")

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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


class LeverGruel(JobGruel):
    """`JobGruel` subclass for Lever job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        return soup.find_all("div", class_="posting")

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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


class BambooGruel(JobGruel):
    """`JobGruel` subclass for BambooHR job boards."""

    @override
    def get_source(self) -> gruel.Response:
        url = f"{self.board.url}/list"
        response = self.request(url)
        if response.url.strip("/") != url:
            raise RuntimeError(f"Board url {url} resolved to {response.url}")
        return response

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[dict[str, Any]]:
        return source.json()["result"]

    @override
    def parse_item(self, item: dict[str, Any]) -> models.Listing | None:
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


class AshbyGruel(JobGruel):
    """`JobGruel` subclass for Ashby job boards."""

    @property
    def api_url(self) -> str:
        return "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"

    @property
    def api_operation_name(self) -> str:
        return "ApiJobBoardWithTeams"

    @property
    def api_variables(self) -> dict[str, str]:
        return {
            "organizationHostedJobsPageName": self.board.url[
                self.board.url.rfind("/") + 1 :
            ].replace("%20", " ")
        }

    @property
    def api_query(self) -> str:
        return "query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {\n  jobBoard: jobBoardWithTeams(\n    organizationHostedJobsPageName: $organizationHostedJobsPageName\n  ) {\n    teams {\n      id\n      name\n      parentTeamId\n      __typename\n    }\n    jobPostings {\n      id\n      title\n      teamId\n      locationId\n      locationName\n      employmentType\n      secondaryLocations {\n        ...JobPostingSecondaryLocationParts\n        __typename\n      }\n      compensationTierSummary\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment JobPostingSecondaryLocationParts on JobPostingSecondaryLocation {\n  locationId\n  locationName\n  __typename\n}"

    @override
    def get_source(self) -> gruel.Response:
        return self.request(
            self.api_url,
            "post",
            headers={
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip, deflate",
            },
            json={
                "operationName": self.api_operation_name,
                "variables": self.api_variables,
                "query": self.api_query,
            },
        )

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[dict[str, Any]]:
        return source.json()["data"]["jobBoard"]["jobPostings"]

    @override
    def parse_item(self, item: dict[str, Any]) -> models.Listing | None:
        listing = self.new_listing()
        listing.position = item["title"]
        listing.url = f"{self.board.url}/{item['id']}"
        listing.location = item["locationName"]
        return listing


class WorkableGruel(JobGruel):
    """`JobGruel` subclass for Workable job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(
            f"https://apply.workable.com/api/v3/accounts/{self.board.url[self.board.url.rfind('/')+1:]}/jobs",
            "post",
        )

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[dict[str, Any]]:
        return source.json()["results"]

    @cached_property
    def base_listing_url(self) -> str:
        return f"https://apply.workable.com/{self.board.url[self.board.url.rfind('/')+1:]}/j"

    @override
    def parse_item(self, item: dict[str, Any]) -> models.Listing | None:
        listing = self.new_listing()
        listing.url = f"{self.base_listing_url}/{item['shortcode']}"
        location = ""
        if item["remote"]:
            location += f"Remote {item['location']['country']}"
        else:
            location += f"{item['location']['city']}, {item['location']['country']}"
        listing.location = location
        listing.position = item["title"]
        return listing


class EasyapplyGruel(JobGruel):
    """`JobGruel` subclass for Easyapply job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        listings = soup.find("div", attrs={"id": "list"})
        assert isinstance(listings, Tag)
        return listings.find_all("a", attrs={"target": "_blank"})

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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


class JobviteGruel(JobGruel):
    """`JobGruel` subclass for Jobvite job boards."""

    def __init__(
        self,
        existing_listings: list[models.Listing] | None = None,
        company_stem: str | None = None,
        board: models.Board | None = None,
    ):
        super().__init__(existing_listings, company_stem, board)
        self._location_tag = ""

    @property
    def location_tag(self) -> str:
        """The location tag type.
        Varies depending on the tag type of the job list container element."""
        return self._location_tag

    @location_tag.setter
    def location_tag(self, tag: str):
        self._location_tag = tag

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        listings: list[Tag] = []
        job_tables: ResultSet[Any] | None = None
        listing_tag = ""
        container_tag = ""
        for container_tag, listing_tag, location_tag in [
            ("table", "tr", "td"),
            ("div", "li", "div"),
            ("ul", "li", "span"),
        ]:
            job_tables = soup.find_all(container_tag, class_="jv-job-list")
            if job_tables:
                self.location_tag = location_tag
                break
        if not job_tables:
            raise RuntimeError(f"Could not find job table.")
        for table in job_tables:
            if isinstance(table, Tag):
                listings.extend(table.find_all(listing_tag))
        if not listings and container_tag == "div":
            for table in job_tables:
                if isinstance(table, Tag):
                    listings.extend(table.find_all("div", class_="jv-job-item"))
        return listings

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
        listing = self.new_listing()
        assert isinstance(item, Tag)
        a = item.find("a")
        assert isinstance(a, Tag)
        listing.url = f"https://jobs.jobvite.com/careers{a.get('href')}"
        listing.position = a.text
        td = item.find(self.location_tag, class_="jv-job-list-location")
        if isinstance(td, Tag):
            listing.location = td.text
        return listing


class ApplytojobGruel(JobGruel):
    """`JobGruel` subclass for ApplyToJob job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        list_group = soup.find("ul", class_="list-group")
        if isinstance(list_group, Tag):
            return list_group.find_all("li", class_="list-group-item")
        return []

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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


class SmartrecruiterGruel(JobGruel):
    """`JobGruel` subclass for SmartRecruiters job boards."""

    @property
    def api_endpoint(self) -> str:
        company_page = self.board.url[self.board.url.rfind("/") + 1 :]
        return f"https://careers.smartrecruiters.com/{company_page}/api/more?page="

    @override
    def get_source(self) -> list[gruel.Response]:
        page_count = 0
        responses: list[gruel.Response] = []
        while True:
            if page_count == 0:
                responses.append(self.request(self.board.url))
            else:
                response = self.request(f"{self.api_endpoint}{page_count}")
                if not response.text:
                    break
                else:
                    response.raise_for_status()
                responses.append(response)
            page_count += 1
        return responses

    @override
    def get_parsable_items(self, source: list[gruel.Response]) -> list[Tag]:
        listings: list[Tag] = []
        for response in source:
            listings.extend(
                response.get_soup().find_all("a", class_="link--block details")
            )
        return listings

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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


class RecruiteeGruel(JobGruel):
    """`JobGruel` subclass for Recruitee job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        output = soup.find("output")
        if not isinstance(output, Tag):
            return []
        div_grid = output.find("div")
        assert isinstance(div_grid, Tag)
        return div_grid.find_all("div", recursive=False)

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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


class RecruiteeAltGruel(JobGruel):
    """Alternative `JobGruel` subclass for Recruitee job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        return soup.find_all("div", class_="job")

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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


class BreezyGruel(JobGruel):
    """`JobGruel` subclass for Breezy job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        return soup.find_all("li", class_="position transition")

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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


class MyworkdayGruel(JobGruel):
    """`JobGruel` subclass for MyWorkDay job boards."""

    @property
    def api_url(self) -> str:
        url = self.board.url
        base = url[: url.find(".com") + 4]
        anchor = url[url.rfind("/") + 1 :]
        if "myworkdaysite" in url:
            company_stem = url[
                url.rfind("/", 0, url.find(anchor) - 1) + 1 : url.rfind("/")
            ]
        else:
            company_stem = url.removeprefix("https://")
            company_stem = company_stem[: company_stem.find(".")]
        company_stem = company_stem.replace("-", "_")
        return f"{base}/wday/cxs/{company_stem}/{anchor}/jobs"

    @override
    def get_source(self) -> list[gruel.Response]:
        response_count = 0
        listings_per_response = 20
        headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        next_response: Callable[[int], gruel.Response] = (
            lambda response_count: self.request(
                self.api_url,
                "post",
                headers=headers,
                json={
                    "limit": str(listings_per_response),
                    "offset": str(response_count * listings_per_response),
                },
            )
        )
        responses: list[gruel.Response] = []
        response = next_response(response_count)
        total_listings = response.json()["total"]
        total_responses = int(total_listings / listings_per_response) + 1
        responses.append(response)
        for response_count in range(1, total_responses):
            responses.append(next_response(response_count))
        return responses

    @override
    def get_parsable_items(self, source: list[gruel.Response]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for response in source:
            items.extend(
                [
                    listing
                    for listing in response.json()["jobPostings"]
                    if "title" in listing
                ]
            )
        return items

    @override
    def parse_item(self, item: dict[str, Any]) -> models.Listing | None:
        listing = self.new_listing()
        listing.position = item["title"]
        listing.url = f"{self.board.url.strip('/')}{item['externalPath']}"
        listing.location = item.get("locationsText", "Unlisted")
        return listing


class TeamtailorGruel(JobGruel):
    """`JobGruel` subclass for TeamTailor job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        job_container = soup.find("ul", attrs={"id": "jobs_list_container"})
        assert isinstance(job_container, Tag)
        return job_container.find_all("li")

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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


class PaycomGruel(JobGruel):
    """`JobGruel` subclass for Paycom job boards."""

    @property
    def base_url(self) -> str:
        return "https://www.paycomonline.net"

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[dict[str, Any]]:
        soup = source.get_soup()
        main_content = soup.find("div", attrs={"id": "main-content"})
        assert isinstance(main_content, Tag)
        data_script = main_content.find_all("script")[0].text.strip()
        data_script = data_script[data_script.find("[") - 1 : data_script.rfind(";")]
        data = json.loads(data_script)
        return data

    @override
    def parse_item(self, item: dict[str, Any]) -> models.Listing | None:
        listing = self.new_listing()
        listing.position = item["title"]
        listing.location = item["location"]["description"]
        listing.url = f"{self.base_url}{item['url']}"
        return listing


class PaylocityGruel(JobGruel):
    """`JobGruel` subclass for Paylocity job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[dict[str, Any]]:
        soup = source.get_soup()
        # Look for `<script> window.pageData = `
        for script in soup.find_all("script"):
            text = script.text.strip(" \n\t\r")
            if text.startswith("window.pageData "):
                text = text[text.find("{") : text.rfind(";")]
                return json.loads(text)["Jobs"]
        raise RuntimeError("Could not find `window.pageData` script.")

    @override
    def parse_item(self, item: dict[str, Any]) -> models.Listing | None:
        listing = self.new_listing()
        listing.position = item["JobTitle"]
        listing.location = item["LocationName"]
        listing.url = (
            f"https://recruiting.paylocity.com/Recruiting/Jobs/Details/{item['JobId']}"
        )
        return listing


class DoverGruel(JobGruel):
    """`JobGruel` subclass for Dover job boards."""

    @property
    def board_id(self) -> str:
        """Returns the id from `self.board.url`."""
        # https://app.dover.io/{company}/careers/{board_id}
        return self.board.url[self.board.url.rfind("/") + 1 :]

    @property
    def api_endpoint(self) -> str:
        return f"https://app.dover.io/api/v1/careers-page/{self.board_id}/jobs"

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.api_endpoint)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[dict[str, Any]]:
        return source.json()["results"]

    @override
    def parse_item(self, item: dict[str, Any]) -> models.Listing | None:
        listing = self.new_listing()
        listing.position = item["title"]
        if item["locations"]:
            listing.location = "\n".join(
                location["name"] for location in item["locations"]
            )
        anchor = ".io/"
        company = self.board.url[
            self.board.url.find(anchor) + len(anchor) : self.board.url.find("/careers/")
        ]
        listing.url = f"https://app.dover.io/apply/{company}/{item['id']}"
        return listing


class RipplingGruel(JobGruel):
    """`JobGruel` subclass for Rippling job boards."""

    @override
    def get_source(self) -> gruel.Response:
        return self.request(self.board.url)

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Tag]:
        soup = source.get_soup()
        return soup.find_all("div", class_="css-cq05mv")

    @override
    def parse_item(self, item: Tag) -> models.Listing | None:
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
