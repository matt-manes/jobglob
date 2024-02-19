from string import ascii_letters, digits
from typing import Callable

import quickpool
import requests
import whosyouragent
from pathier import Pathier
from scrapetools import LinkScraper
from younotyou import younotyou

from board_meta import BoardMeta

root = Pathier(__file__).parent


class BoardDetector:
    """Various methods of trying to detect what, if any, 3rd party job board(s) a company uses."""

    def __init__(self):
        self.load_meta()
        self.load_careers_page_stubs()

    @property
    def boards(self) -> list[str]:
        return self.meta.boards

    @property
    def careers_page_stubs(self) -> list[str]:
        return self._careers_page_stubs

    @property
    def meta(self) -> BoardMeta:
        return self._meta

    @property
    def url_chunk_mapping(self) -> dict[str, str]:
        """Get url chunk to board type mapping."""
        return self.meta.url_chunks

    @property
    def url_template_mapping(self) -> dict[str, str]:
        """Get board type to url template mapping."""
        return self.meta.url_templates

    def load_meta(self):
        """Load `board_meta.toml`."""
        self._meta = BoardMeta.load()

    def load_careers_page_stubs(self):
        """Load `careers_page_stubs.txt`."""
        self._careers_page_stubs = (root / "careers_page_stubs.txt").split()

    def request(self, url: str) -> requests.Response:
        """Send a request to `url` and return the response."""
        return requests.get(
            url, headers={"User-Agent": whosyouragent.get_agent()}, timeout=10
        )

    def get_stem_permutations(self, company: str) -> list[str]:
        """Returns permutations of a company name.

        e.g. "Company Inc." returns
        "companyinc"
        "company-inc"
        "company inc"
        "CompanyInc"
        """
        alphanum = ascii_letters + digits + " -"
        stems = [company]
        company_parts = company.split()
        stems.extend(["".join(company_parts), "-".join(company_parts)])
        stems.extend([stem.lower() for stem in stems])
        stems.extend(["".join((ch for ch in stem if ch in alphanum)) for stem in stems])
        return list(set(stems))

    def get_possible_urls(self, company: str, board_type: str) -> list[str]:
        """Returns a list of potentially valid urls given a `company` and a `board_type`."""
        template_url = self.url_template_mapping[board_type]
        stems = self.get_stem_permutations(company)
        return [template_url.replace("$company", stem) for stem in stems]

    def get_board_type_from_text(self, text: str) -> str | None:
        """Returns the board type by searching `text`.

        Returns `None` if `text` doesn't match any chunks in `board_meta.toml`."""
        for chunk in self.url_chunk_mapping:
            if chunk in text:
                return self.url_chunk_mapping[chunk]
        return None

    def get_board_type_from_page(self, url: str) -> str | None:
        """Makes a request to `url` and scans the returned content to determine the board type.

        Returns `None` if the board type could not be detected."""
        try:
            response = self.request(url)
            return self.get_board_type_from_text(response.text)
        except Exception as e:
            print(e)
            return None

    def response_is_valid(
        self, response: requests.Response, requested_url: str
    ) -> bool:
        """Returns `True` if `response.status_code == 200` and `response.url` matches `requested_url`, i.e. no redirect."""
        return (
            True
            if response.status_code == 200 and response.url.strip("/") == requested_url
            else False
        )

    def get_valid_urls(self, urls: list[str]) -> list[str] | None:
        """Make a request to each url in `urls`.

        Returns a list of the urls that return a 200 status code and don't redirect to a different url.
        """
        valid_urls: list[str] = []
        for url in urls:
            try:
                response = self.request(url)
                if self.response_is_valid(response, url) and (
                    "ashbyhq.com" not in url
                    or '"organization":null' not in response.text.lower()
                ):
                    # ashby returns a 200 even if the company doesn't exist with them
                    valid_urls.append(url)
            except Exception as e:
                ...
        # Some are case sensitive and some aren't (seems like mostly lever.co)
        # Return just a lower case url if the only results are the same two urls except for case
        if len(valid_urls) == 2 and valid_urls[0].lower() == valid_urls[1].lower():
            valid_urls = [valid_urls[0].lower()]
        return valid_urls or None

    def get_board_by_brute_force(self, company: str) -> list[str]:
        """Just try all the templates for a company name and see what sticks.

        Returns a list of urls that appear valid."""
        # Slightly different from self.boards b/c this includes greenhouse_embed
        board_types = list(self.url_template_mapping.keys())
        try_board: Callable[[str, str], list[str] | None] = (
            lambda company, board_type: self.get_valid_urls(
                self.get_possible_urls(company, board_type)
            )
        )
        pool = quickpool.ThreadPool(
            [try_board] * len(board_types),
            [(company, board_type) for board_type in board_types],
        )
        results = [result for result in pool.execute() if result]
        candidate_urls: list[str] = []
        for result in results:
            candidate_urls.extend(result)
        return candidate_urls

    def scrape_page_for_boards(self, url: str) -> list[str]:
        """Make a request to `url` and scrape the page for links containing the substrings in `self.boards`."""
        try:
            response = self.request(url)
        except Exception as e:
            return []
        linkscraper = LinkScraper(response.text, url)
        linkscraper.scrape_page()
        links = linkscraper.get_links(excluded_links=linkscraper.get_links("img"))
        boards = [f"*{board}*" for board in self.boards]
        urls = younotyou(links, boards, case_sensitive=False)
        return urls

    def get_careers_page_by_brute_force(self, base_url: str) -> list[str | None]:
        """Given `base_url`, try requesting it with the page stubs in `careers_page_stubs.txt`.

        Returns a list of urls that returned a 200 code and didn't redirect."""
        base_url = base_url.strip("/")
        pages = (root / "careers_page_stubs.txt").split()
        urls = [f"{base_url}/{page}" for page in pages]

        def try_page(url: str) -> requests.Response | None:
            try:
                return self.request(url)
            except Exception as e:
                return None

        results = quickpool.ThreadPool(
            [try_page] * len(urls), [(url,) for url in urls]
        ).execute(False)
        return [
            url
            for url, response in zip(urls, results)
            if response and self.response_is_valid(response, url)
        ]

    def scrape_for_careers_page(self, url: str) -> list[str]:
        """Scrape a url for urls matching the stubs in `careers_page_stubs.txt`.

        Returns a list of any matching urls."""
        try:
            linkscraper = LinkScraper(self.request(url).text, url)
        except Exception as e:
            return []
        linkscraper.scrape_page()
        terms = [
            f"*{term}*"
            for term in self.careers_page_stubs
            if term not in ["get-involved"]
        ]
        return younotyou(linkscraper.get_links(), terms, case_sensitive=False)
