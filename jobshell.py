import os
import webbrowser
from datetime import datetime

import argshell
from databased.dbshell import DBShell
from pathier import Pathier

import board_detector
import company_crawler
import dump_data
import helpers
import jobglob
import models
import peruse
from config import Config
from jobbased import JobBased

root = Pathier(__file__).parent


def num_days(date: datetime) -> int:
    """Returns the number of days since 'date'."""
    return (datetime.now() - date).days


def get_add_listing_parser() -> argshell.ArgShellParser:
    """Returns an `add_listing` parser."""
    parser = argshell.ArgShellParser(prog="")
    parser.add_argument("position", type=str, help=" The job title of the listing. ")
    parser.add_argument("company", type=str, help=" The company the listing is for. ")
    parser.add_argument("url", type=str, help=" The url of the listing. ")
    parser.add_argument(
        "-l",
        "--location",
        type=str,
        default="Remote",
        help=' The location of the listing. Defaults to "Remote". ',
    )
    parser.add_argument(
        "-a", "--applied", action="store_true", help=" Mark this listing as 'applied'. "
    )
    return parser


def get_add_board_parser() -> argshell.ArgShellParser:
    """Returns a `add_board` parser."""
    parser = argshell.ArgShellParser()
    parser.add_argument("url", type=str, help=" Job board url.3 ")
    parser.add_argument("company", type=str, help=" Company name. ")
    parser.add_argument(
        "-b",
        "--board_type",
        type=str,
        default=None,
        help=" Specify a board type instead of trying to detect one. ",
    )
    return parser


def get_toggle_scraper_parser() -> argshell.ArgShellParser:
    """Returns a `toggle_scraper` parser."""
    parser = argshell.ArgShellParser(
        "toggle_scraper", description="Activate or deactivate scrapers/boards."
    )
    parser.add_argument(
        "status",
        choices=["a", "d"],
        type=str,
        default=None,
        help=" Whether the boards should be activated (a) or deactivated (d).",
    )
    parser.add_argument(
        "scrapers",
        nargs="*",
        type=str,
        default=[],
        help=" A list of board ids or company stems to toggle.",
    )
    return parser


def get_crawl_company_parser() -> argshell.ArgShellParser:
    """Returns a `crawl_company` parser."""
    parser = company_crawler.get_company_crawler_parser()
    parser.add_argument("homepage", type=str, help=""" The url to start crawling at.""")
    return parser


class JobShell(DBShell):
    _dbpath = Pathier("jobs.db")
    intro = "Starting job_manager (enter help or ? for command info)..."
    prompt = "jobshell>"
    common_commands = [
        "schema",
        "jobglob",
        "mark_applied",
        "quit",
        "mark_dead",
        "backup",
        "mark_rejected",
        "peruse",
        "pin_listing",
        "pinned",
        "add_scraper",
        "toggle_scraper",
        "select",
        "apps",
    ]
    common_commands = sorted(set(common_commands))
    log_dir = Config.load().logs_dir

    @argshell.with_parser(get_add_listing_parser)
    def do_add_listing(self, args: argshell.Namespace):
        """Add a job listing to the database."""
        with JobBased(self.dbpath) as db:
            company = db.get_company_from_name(args.company)
            if not company:
                db.add_company(args.name)
                company = db.get_company_from_name(args.name)
                assert company
            db.add_listing(
                models.Listing(
                    company,
                    position=args.position,
                    location=args.location,
                    url=args.url,
                )
            )
            if args.applied:
                listing = db._get_listings(f"url = '{args.url}'")[0]
                db.add_application(listing.id_)

    @argshell.with_parser(get_add_board_parser)
    def do_add_scraper(self, args: argshell.Namespace):
        """Add a scraper to the list."""
        with JobBased(self.dbpath) as db:
            args.url = args.url.strip("/")
            if args.url in [board.url for board in db.get_boards()]:
                print("That board already exists.")
            else:
                db.add_board(args.url, args.company)
                helpers.create_scraper_from_template(
                    args.url, args.company, args.board_type
                )

    def do_apps(self, _: str):
        """Display submitted applications data."""
        with JobBased(self.dbpath) as db:
            self.display(db.select("apps"))

    def do_company_exists(self, company: str):
        """Return info about `company` if it exists in the database."""
        with JobBased(self.dbpath) as db:
            where = f"company LIKE '%{company}%'"
            if db.count("scrapers", where=where):
                data = db.select("scrapers", where=where)
                self.display(data)
            else:
                print(f"Could not find records matching '%{company}%'.")

    @argshell.with_parser(get_crawl_company_parser)
    def do_crawl_company(self, args: argshell.Namespace):
        """Crawl company homepage for job board urls."""
        crawler = company_crawler.Crawler(
            args.homepage, args.max_depth, args.max_time, args.max_hits, args.debug
        )
        crawler.crawl()

    def do_dump(self, _: str):
        """Dump data for `companies`, `boards`, and `listings` tables to `sql/jobs_data.sql`."""
        print("Creating dump file...")
        dump_data.dump()

    def do_find_boards(self, url: str):
        """Try to detect job board urls from a company website."""
        detector = board_detector.BoardDetector()
        boards = []
        boards = detector.scrape_page_for_boards(url)
        if not boards:
            careers_urls = detector.scrape_for_careers_page(url)
            for url in careers_urls:
                boards.extend(detector.scrape_page_for_boards(url))
        if not boards:
            print("Could not find any job boards.")
        else:
            print(f"Found {len(boards)} possible board urls:")
            print(*boards, sep="\n")

    def do_find_careers_page(self, base_url: str):
        """Try to find the careers page given a company's base url."""
        detector = board_detector.BoardDetector()
        urls = detector.get_careers_page_by_brute_force(base_url)
        if urls:
            print(*urls, sep="\n")
        else:
            print("Valid urls not found.")

    def do_generate_peruse_filters_file(self, _: str):
        """Generate a file named `peruse_filters.toml` that is empty besides categories.

        Each category should be filled with a list of strings."""
        helpers.create_peruse_filters_from_template()

    def do_help(self, cmd: str):
        """Display help messages."""
        print()
        if not cmd:
            header = "Common commands (type help <topic>):"
            self.print_topics(header, self.common_commands, 15, 80)
        super().do_help(cmd)

    def do_jobglob(self, _: str):
        """Scrape active job boards."""
        jobglob.main()

    def do_mark_applied(self, listing_id: str):
        """Mark a job as applied given the `listing_id`."""
        with JobBased(self.dbpath) as db:
            db.add_application(int(listing_id))

    def do_mark_dead(self, listing_id: str):
        """Given a `listing_id`, mark a listing as removed."""
        with JobBased(self.dbpath) as db:
            db.mark_dead(int(listing_id))

    def do_mark_rejected(self, application_id: str):
        """Mark a job as rejected given the `application_id`."""
        with JobBased(self.dbpath) as db:
            db.mark_rejected(int(application_id))

    def do_open(self, company: str):
        """Open the board url associated with the given company."""
        with JobBased() as db:
            url = db.get_board(company).url
        webbrowser.open_new_tab(url)

    @argshell.with_parser(peruse.get_peruse_parser, [peruse.lower_terms])
    def do_peruse(self, args: argshell.Namespace):
        """Look through unseen job listings."""
        peruse.main(args)

    def do_pin_listing(self, listing_id: str):
        """Pin a listing given its `listing_id`."""
        with JobBased() as db:
            db.pin_listing(int(listing_id))

    def do_pinned(self, arg: str):
        """Display pinned listings.

        Add `live` to this command to only show live listings."""
        with JobBased(self.dbpath) as db:
            self.display(
                db.select(
                    "pinned",
                    ["l_id", "position", "company", "url", "age_days", "alive"],
                    where="alive = 1" if arg == "live" else "1 = 1",
                )
            )

    def do_reset_alive_status(self, listing_ids: str):
        """Reset the status of a listing to alive given a list of `listing_id`s."""
        with JobBased(self.dbpath) as db:
            for id_ in listing_ids.split():
                db.reset_alive_status(int(id_))

    @argshell.with_parser(get_toggle_scraper_parser)
    def do_toggle_scraper(self, args: argshell.Namespace):
        """Activate or deactivate scrapers/boards."""
        active = 1 if args.status == "a" else 0
        with JobBased() as db:
            for scraper in args.scrapers:
                try:
                    where = f"board_id = {int(scraper)}"
                except Exception as e:
                    company = db.get_company_from_name(helpers.stem_to_name(scraper))
                    assert company
                    where = f"company_id = {company.id_}"
                print(
                    f"{scraper} updated: {db.update('boards', 'active', active, where)}"
                )

    def do_trouble_shoot(self, file_stem: str):
        """Show scraper entry and open {file_stem}.py and {file_stem}.log."""
        config = Config.load()
        self.do_open(file_stem)
        company = file_stem.replace("_", " ")
        with JobBased(self.dbpath) as db:
            self.display(db.select("scrapers", where=f"company LIKE '{company}'"))
        os.system(f"code {config.scrapers_dir}/{file_stem}.py -r")
        os.system(f"code {config.scraper_logs_dir}/{file_stem}.log -r")

    def do_try_boards(self, company: str):
        """Just try all template urls and see what sticks given a company name."""
        detector = board_detector.BoardDetector()
        urls = detector.get_board_by_brute_force(company)
        if urls:
            print(*urls, sep="\n")
        else:
            print(urls)


if __name__ == "__main__":
    JobShell().cmdloop()
