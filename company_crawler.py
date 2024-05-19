import warnings
from collections import deque

import argshell
import gruel
import loggi
from pathier import Pathier, Pathish
from rich import print
from typing_extensions import Any, Sequence, override
from younotyou import Matcher, younotyou

from config import Config

warnings.filterwarnings("ignore")

root = Pathier(__file__).parent


class MaxHitsLimit(gruel.CrawlLimit):
    """
    Limit for number of ATS urls found.
    """

    def __init__(self, max_hits: int | None, board_urls: deque[str]):
        self.max_hits = max_hits
        self.board_urls = board_urls

    @property
    @override
    def exceeded(self) -> bool:
        if self.max_hits:
            return len(self.board_urls) >= self.max_hits
        return False

    def __str__(self) -> str:
        return f"Max hits of {self.max_hits} exceeded."

    def __rich__(self) -> str:
        return f"Max hits of [bright_red]{self.max_hits}[/] exceeded."


class BoardScraper(gruel.CrawlScraper):
    def __init__(
        self,
        company: str,
        save_path: Pathier | None = None,
        max_hits: int | None = None,
    ):
        super().__init__()
        config = Config.load()
        self.board_urls: deque[str] = deque()
        self.urls_with_stubs: dict[str, set[str]] = {}
        self.board_stubs = [
            f"*{board}*" for board in config.board_meta_path.loads()["url_chunks"]
        ]
        self.max_hits = MaxHitsLimit(max_hits, self.board_urls)
        self.save_path = save_path
        self.company = company

    def fix_board_urls(self, urls: list[str]) -> list[str]:
        """
        Make certain substring swaps in `urls`.

        * `/js?` -> `?` (greenhouse)
        * `bamboohr.com/js/embed.js` -> `bamboohr.com/careers`
        """
        swaps = [
            ("/js?", "?"),
            ("bamboohr.com/js/embed.js", "bamboohr.com/careers"),
        ]
        for swap in swaps:
            urls = [url.replace(swap[0], swap[1]) for url in urls]
        return urls

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[Any]:
        linkscraper = source.get_linkscraper()
        linkscraper.scrape_page()
        # get all non-image urls that point to the website being scraped
        # these will be used to reduce the number of urls passed to `younotyou`
        same_site_urls = linkscraper.get_links(
            "page", excluded_links=linkscraper.get_links("img"), same_site_only=True
        )
        # get urls that match any of the ones in `board_stubs`
        board_urls = younotyou(
            linkscraper.get_links(excluded_links=same_site_urls),
            self.board_stubs,
            case_sensitive=False,
        )
        self.logger.info(f"{linkscraper.get_links()}=")
        self.logger.info(f"Found {len(board_urls)} board urls on `{source.url}`.")
        if board_urls:
            board_urls = self.fix_board_urls(board_urls)
            for url in board_urls:
                self.board_urls.append(url)
        else:
            # Look for any ATS stubs if no actual board urls were found.
            for stub in self.board_stubs:
                stub = stub.strip("*")
                if stub in source.text:
                    self.urls_with_stubs.setdefault(source.url, set())
                    self.urls_with_stubs[source.url].add(stub)
                    self.logger.info(f"Found `{stub}` on `{source.url}`.")
        return []

    @override
    def parse_item(self, item: str) -> str:
        # don't actually need to utilize this function in this case
        return item

    @override
    def store_items(self, items: Sequence[Any]) -> None:
        # don't actually need to utilize this function in this case
        pass

    @override
    def postscrape_chores(self):
        super().postscrape_chores()
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
        self.save_results()

    def save_results(self):
        """Save results to json file."""
        if self.save_path and (self.board_urls or self.urls_with_stubs):
            data = self.save_path.loads()
            data.setdefault(self.company, {})
            if self.board_urls:
                data[self.company]["board_urls"] = list(set(self.board_urls))
            if self.urls_with_stubs:
                data[self.company]["urls_with_stubs"] = list(set(self.urls_with_stubs))
            self.save_path.dumps(data, indent=2, default=str)


class UrlManager(gruel.UrlManager, loggi.LoggerMixin):
    @override
    def __init__(self):
        super().__init__()
        config = Config.load()
        self.career_page_stubs = Matcher(
            [f"*{stub}*" for stub in config.careers_page_stubs_path.split()],
            case_sensitive=False,
        )
        self.init_logger()

    @override
    def add_urls(self, urls: Sequence[str]):
        for url in urls:
            # prioritize career/job pages
            if url in self.career_page_stubs:
                self._uncrawled.appendleft(url)
            else:
                self._uncrawled.append(url)


class CompanyCrawler(gruel.Crawler):
    @override
    def __init__(
        self,
        scraper: BoardScraper,
        max_depth: int | None = None,
        max_time: float | None = None,
        name: str | int | loggi.LogName = loggi.LogName.FILENAME,
        log_dir: Pathish = "logs",
        max_threads: int = 3,
        same_site_only: bool = True,
        custom_url_manager: UrlManager | None = None,
    ):
        super().__init__(
            [scraper],
            max_depth,
            max_time,
            name,
            log_dir,
            max_threads,
            same_site_only,
            custom_url_manager or UrlManager(),
        )
        self.url_manager: UrlManager
        self.scraper: BoardScraper

    @override
    def postscrape_chores(self):
        super().postscrape_chores()
        self.url_manager.logger.close()


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


def minutes_to_seconds(args: argshell.Namespace) -> argshell.Namespace:
    if args.max_time:
        args.max_time *= 60
    return args


def get_args() -> argshell.Namespace:
    return get_company_crawler_parser().parse_args()


def main(args: argshell.Namespace | None = None):
    """Scrape a list of companies from `company_crawler.txt` and save the results to `crawled_companies.json`.

    `company_crawler.txt` should be one company per line in the format: `{url} {company name}`.
    """
    if not args:
        args = get_args()
    args = minutes_to_seconds(args)
    companies = (root / "company_crawler.txt").split()
    save_path = root / "crawled_companies.json"
    if not save_path.exists():
        save_path.dumps({})
    num_crawls = len(companies)
    for i, line in enumerate(companies, 1):
        print(f"Crawling company {i}/{num_crawls}")
        url, company = line.split(maxsplit=1)
        crawler = CompanyCrawler(
            BoardScraper(company, save_path, args.max_hits),
            max_depth=args.max_depth,
            max_time=args.max_time,
        )
        crawler.crawl(url)


if __name__ == "__main__":
    main(get_args())
