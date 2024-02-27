import os
import webbrowser
from datetime import datetime, timedelta

import argshell
from databased.dbshell import DBShell
from noiftimer import time_it
from pathier import Pathier
from rich import print

import board_detector
import company_crawler
import dump_data
import helpers
import jobglob
import logglob
import models
import peruse
import shellparsers
from config import Config
from jobbased import JobBased

root = Pathier(__file__).parent


def num_days(date: datetime) -> int:
    """Returns the number of days since 'date'."""
    return (datetime.now() - date).days


class JobShell(DBShell):
    _dbpath = Pathier("jobs.db")
    common_commands = [
        "schema",
        "jobglob",
        "glob",
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
    intro = "Starting job_manager (enter help or ? for command info)..."
    log_dir = Config.load().logs_dir
    prompt = "jobshell>"

    @argshell.with_parser(shellparsers.get_add_listing_parser)
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

    @argshell.with_parser(shellparsers.get_add_board_parser)
    def do_add_scraper(self, args: argshell.Namespace):
        """Add a scraper to the list."""
        with JobBased(self.dbpath) as db:
            args.url = args.url.strip("/")
            if args.url in [board.url for board in db.get_boards()]:
                print("That board already exists.")
            else:
                db.add_board(args.url, args.company)
                if not board_detector.BoardDetector().get_board_type_from_text(
                    args.url
                ):
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

    @argshell.with_parser(shellparsers.get_crawl_company_parser)
    def do_crawl_company(self, args: argshell.Namespace):
        """Crawl company homepage for job board urls."""
        crawler = company_crawler.Crawler(
            args.homepage, args.max_depth, args.max_time, args.max_hits, args.debug
        )
        crawler.crawl()

    def do_create_scraper_file(self, company: str):
        """Create a scraper file from a template for the given company name or stem.

        Use when a scraper exists in the database, but needs custom functionality."""
        stem = helpers.name_to_stem(company)
        with JobBased(self.dbpath) as db:
            try:
                board = db.get_board(stem)
            except ValueError:
                print(f"Could not find a board for '{company}' in the database.")
            else:
                helpers.create_scraper_from_template(board.url, board.company.name)

    def do_dump(self, _: str):
        """Dump data for `companies`, `boards`, and `listings` tables to `sql/jobs_data.sql`."""
        print("Creating dump file...")
        dump_data.dump()

    @time_it()
    def do_empty_boards(self, _: str):
        """Display scrapers that found no listings on their last run."""
        with self.console.status(
            "[pink1]Searching for empty boards...",
            spinner_style="deep_pink1",
            spinner="arc",
        ):
            empty_boards = logglob.get_empty_boards()
        empty_boards = [helpers.stem_to_name(board) for board in empty_boards]
        with JobBased(self.dbpath) as db:
            scrapers = db.get_scrapers_from_companies(empty_boards)
        self.display(scrapers)
        self.console.print(f"[turquoise2]{len(scrapers)} [pink1]results.")

    def do_generate_peruse_filters_file(self, _: str):
        """Generate a file named `peruse_filters.toml` that is empty besides categories.

        Each category should be filled with a list of strings."""
        helpers.create_peruse_filters_from_template()

    def do_glob(self, company: str):
        """Run the scraper for the given company."""
        stem = helpers.name_to_stem(company)
        with JobBased() as db:
            board = db.get_board(stem)
        class_ = jobglob.ScraperLoader().get_scraper_class(board)
        if not class_:
            print(
                f"No scraper class could be found for {company}"
                + (f"({stem})" if stem != company else "")
            )
        else:
            start = datetime.now() - timedelta(seconds=2)
            scraper = class_(board=board)
            scraper.scrape()
            print(logglob.load_log(scraper.board.company.name).filter_dates(start))

    def do_help(self, arg: str):
        """Display help messages."""
        print()
        if not arg:
            header = "Common commands (type help <topic>):"
            self.print_topics(header, self.common_commands, 15, 80)
        super().do_help(arg)

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

    @argshell.with_parser(peruse.get_peruse_parser, [peruse.peruse_postparser])
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
                    ["l_id", "a_id", "position", "company", "url", "age_days", "alive"],
                    where="alive = 1" if arg == "live" else "1 = 1",
                )
            )

    def do_reset_alive_status(self, listing_ids: str):
        """Reset the status of a listing to alive given a list of `listing_id`s."""
        with JobBased(self.dbpath) as db:
            for id_ in listing_ids.split():
                db.reset_alive_status(int(id_))

    @argshell.with_parser(shellparsers.get_toggle_scraper_parser)
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
        scraper_file = config.scrapers_dir / f"{file_stem}.py"
        if scraper_file.exists():
            os.system(f"code {scraper_file} -r")
        os.system(f"code {config.scraper_logs_dir}/{file_stem}.log -r")

    def do_try_boards(self, company: str):
        """Just try all template urls and see what sticks given a company name."""
        detector = board_detector.BoardDetector()
        urls = detector.get_board_by_brute_force(company)
        if urls:
            print(*urls, sep="\n")
        else:
            print(urls)

    @argshell.with_parser(shellparsers.get_update_board_url_parser)
    def do_update_board_url(self, args: argshell.Namespace):
        """Update the board url for the given board id to the given url."""
        print(f"Updating url for board id `{args.id}` to `{args.url}`...")
        with JobBased(self.dbpath) as db:
            count = db.update_board_url(args.id, args.url)
        print(f"Updated {count} records.")


if __name__ == "__main__":
    JobShell().cmdloop()
