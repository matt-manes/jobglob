import time
import warnings
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache

import argshell
import requests
from gruel import Gruel
from pathier import Pathier
from printbuddies import ProgBar, Spinner
from scrapetools import LinkScraper
from younotyou import Matcher, younotyou

from config import Config

warnings.filterwarnings("ignore")

root = Pathier(__file__).parent


class Crawler(Gruel):
    """Crawl a website for external job board links."""

    def __init__(
        self,
        homepage: str,
        max_depth: int | None = None,
        max_time: float | None = None,
        max_hits: int | None = None,
        debug: bool = False,
    ):
        """
        #### :params:

        `homepage`: The url to start crawling from.

        `max_depth`: Stop crawling after this many pages, if given.

        `max_time`: Stop crawling after this many minutes, if given.

        `max_hits`: Stop crawling after this many hits, if given.
        """
        config = Config.load()
        super().__init__(log_dir=config.logs_dir)
        self.scraped_urls: deque[str] = deque()
        self.new_urls: deque[str] = deque([homepage])
        self.board_urls: deque[str] = deque()
        # Help detect embedded boards by searching response text for stubs.
        # Keys are urls and values are a set of stubs found on that url.
        self.urls_with_stubs: dict[str, set] = {}
        self.max_threads: int = 3
        self.workers: list[Future] = []
        self.max_depth: int | None = max_depth
        self.max_time: float | None = max_time
        self.max_hits: int | None = max_hits
        # max_time should be given in minutes
        if self.max_time:
            self.max_time *= 60
        self.board_stubs = [
            f"*{board}*" for board in config.board_meta_path.loads()["url_chunks"]
        ]
        self.career_page_stubs = Matcher(
            [f"*{stub}*" for stub in config.careers_page_stubs_path.split()],
            case_sensitive=False,
        )
        if debug:
            self.logger.setLevel("DEBUG")

    def _get_finished_workers(self) -> list[Future]:
        """Returns a list of finished futures."""
        return [worker for worker in self.workers if worker.done()]

    def _get_unfinished_workers(self) -> list[Future]:
        """Returns a list of unfinished futures."""
        return [worker for worker in self.workers if not worker.done()]

    def _get_running_workers(self) -> list[Future]:
        """Returns a list of currently executing futures."""
        return [worker for worker in self.workers if worker.running()]

    @property
    def max_depth_exceeded(self) -> bool:
        """Returns `True` if the crawl has a max depth and it has been exceeded."""
        if not self.max_depth:
            return False
        return len(self._get_finished_workers()) > self.max_depth

    @property
    def max_time_exceeded(self) -> bool:
        """Returns `True` if the crawl has a max time and it has been exceeded."""
        if not self.max_time:
            return False
        else:
            return self.timer.elapsed > self.max_time

    @property
    def max_hits_exceeded(self) -> bool:
        """Returns `True` if the crawl has a max hits and it has been exceeded."""
        if not self.max_hits:
            return False
        else:
            return len(set(self.board_urls)) >= self.max_hits

    def _cancel_workers(self):
        """Attempt to cancel any unfinished futures."""
        for worker in self._get_unfinished_workers():
            worker.cancel()

    def _add_new_urls(self, urls: list[str]):
        """Add `urls` to `self.new_urls`.

        Adds a url to the front if it matches any career page stubs."""
        for url in urls:
            # prioritize career/job pages
            if url in self.career_page_stubs:
                self.new_urls.appendleft(url)
            else:
                self.new_urls.append(url)

    def _fix_board_urls(self, urls: list[str]) -> list[str]:
        """Make certain substring swaps in `urls`.

        * `/js?` -> `?` (greenhouse)
        * `bamboohr.com/js/embed.js` -> `bamboo.com/careers`"""
        swaps = [
            ("/js?", "?"),
            ("bamboohr.com/js/embed.js", "bamboo.com/careers"),
        ]
        for swap in swaps:
            urls = [url.replace(swap[0], swap[1]) for url in urls]
        return urls

    def _extract_urls(self, response: requests.Response) -> tuple[list[str], list[str]]:
        """Process `response` for urls and return a tuple containing `same_site_urls` and `board_urls`."""
        linkscraper = LinkScraper(response.text, response.url)
        linkscraper.scrape_page()
        same_site_urls = linkscraper.get_links(
            "page", excluded_links=linkscraper.get_links("img"), same_site_only=True
        )
        board_urls = younotyou(
            linkscraper.get_links(excluded_links=same_site_urls),
            self.board_stubs,
            case_sensitive=False,
        )
        if not board_urls:
            for stub in self.board_stubs:
                stub = stub.strip("*")
                self.logger.debug(f"Looking for stub `{stub}`")
                if stub in response.text:
                    self.urls_with_stubs.setdefault(response.url, set())
                    self.urls_with_stubs[response.url].add(stub)
                    self.logger.info(f"Found {stub} on {response.url}.")
        return same_site_urls, board_urls

    @lru_cache(None)
    def _scrape_page(self, url: str):
        """Scrape `url` for job boards and more urls to scrape."""
        self.logger.info(f"Scraping {url}")
        response = self.request(url, timeout=10, retry_on_fail=False)
        same_site_urls, board_urls = self._extract_urls(response)
        if board_urls:
            self.logger.info(f"Found {len(board_urls)} board urls on {url}")
            board_urls = self._fix_board_urls(board_urls)
            self.board_urls.extend(board_urls)
        if same_site_urls:
            new_urls = [
                site_url
                for site_url in same_site_urls
                if not site_url.startswith("http:")
                and site_url not in [self.new_urls + self.scraped_urls]
            ]
            self.logger.debug(
                f"Found {len(new_urls)} new urls on {url}:\n" + "\n".join(new_urls)
            )
            self._add_new_urls(new_urls)

    def _limits_exceeded(self) -> bool:
        """Check if crawl limits have been exceeded."""
        message = None
        if self.max_depth_exceeded:
            message = f"Max depth of {self.max_depth} exceeded."
        elif self.max_time_exceeded:
            message = f"Max time of {self.timer.format_time(self.max_time)} exceeded."  # type: ignore
        elif self.max_hits_exceeded:
            message = f"Max board hits of {self.max_hits} exceeded."
        if message:
            print()
            self.logger.logprint(message)
            return True
        return False

    def _dispatch_workers(self, executor: ThreadPoolExecutor):
        """Dispatch workers if there are open slots and new urls to be scraped."""
        num_open_slots = self.max_threads - len(self._get_running_workers())
        i = 0
        while i < num_open_slots:
            if not self.new_urls:
                break
            url = self.new_urls.popleft()
            if url not in self.scraped_urls:
                self.scraped_urls.append(url)
                self.workers.append(executor.submit(self._scrape_page, url))
                i += 1

    def postscrape_chores(self):
        self.logger.logprint(f"Crawl completed in {self.timer.elapsed_str}.")
        if self.board_urls:
            self.logger.logprint(f"Boards found:\n" + "\n".join(set(self.board_urls)))
        elif self.urls_with_stubs:
            self.logger.logprint("No boards found.")
            self.logger.logprint(
                f"Found urls with board stubs:\n"
                + "\n".join(
                    f"{url} - {', '.join(stubs)}"
                    for url, stubs in self.urls_with_stubs.items()
                )
            )
        else:
            self.logger.logprint("No boards or stubs found.")
        super().postscrape_chores()

    def _shutdown(self):
        """Attempt to cancel remaining futures and wait for running futures to finish."""
        if len(self._get_finished_workers()) < len(self.workers):
            print("Attempting to cancel remaining workers...")
            self._cancel_workers()
        if running_workers := self._get_running_workers():
            print(f"Waiting for {len(running_workers)} workers to finish...")
            with Spinner(width_ratio=0.15) as spinner:
                while self._get_running_workers():
                    spinner.display()
                    time.sleep(0.1)

    def crawl(self):
        self.timer.start()
        self.logger.logprint(
            f"Starting crawl ({datetime.now():%H:%M:%S}) at {self.new_urls[0]}"
        )
        with ThreadPoolExecutor(self.max_threads) as executor:
            with ProgBar(1, width_ratio=0.3) as bar:
                while (
                    self.new_urls or self._get_unfinished_workers()
                ) and not self._limits_exceeded():
                    self._dispatch_workers(executor)
                    num_finished = len(self._get_finished_workers())
                    total = len(self.workers) + len(self.new_urls)
                    bar.display(
                        f"{bar.runtime}-{num_finished}/{total} urls",
                        counter_override=num_finished,
                        total_override=total,
                    )
                    time.sleep(0.1)
            self._shutdown()
        self.postscrape_chores()


def get_company_crawler_parser() -> argshell.ArgShellParser:
    parser = argshell.ArgShellParser(
        prog="Company crawler", description=""" Crawl a company for job boards. """
    )
    parser.add_argument(
        "-d",
        "--max_depth",
        type=int,
        default=None,
        help=""" The max number of urls to crawl.""",
    )
    parser.add_argument(
        "-t",
        "--max_time",
        type=float,
        default=None,
        help=""" The max time to crawl in minutes.""",
    )
    parser.add_argument(
        "-H",
        "--max_hits",
        type=int,
        default=None,
        help=""" The max hits to crawl for.""",
    )
    parser.add_argument(
        "--debug", action="store_true", help=""" Set logger to debug."""
    )
    return parser


def get_args() -> argshell.Namespace:
    return get_company_crawler_parser().parse_args()


def main(args: argshell.Namespace | None = None):
    """Scrape a list of companies from `company_crawler.txt` and save the results to `crawled_companies.json`.

    `company_crawler.txt` should be one company per line in the format: `{url} {company name}`.
    """
    if not args:
        args = get_args()
    companies = (root / "company_crawler.txt").split()
    save_path = root / "crawled_companies.json"
    if not save_path.exists():
        save_path.dumps({})
    num_crawls = len(companies)
    for i, line in enumerate(companies, 1):
        print(f"Crawling company {i}/{num_crawls}")
        url, company = line.split(maxsplit=1)
        crawler = Crawler(
            url, args.max_depths, args.max_time, args.max_hits, args.debug
        )
        crawler.crawl()
        if crawler.board_urls or crawler.urls_with_stubs:
            data = save_path.loads()
            if crawler.board_urls:
                data[line]["board_urls"] = list(set(crawler.board_urls))
            elif crawler.urls_with_stubs:
                data[line]["urls_with_stubs"] = crawler.urls_with_stubs
            save_path.dumps(data, indent=2, default=str)


if __name__ == "__main__":
    main(get_args())
