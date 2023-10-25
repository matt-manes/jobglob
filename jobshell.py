import os
import webbrowser
from datetime import datetime

import argshell
from databased.dbshell import DBShell
from pathier import Pathier

import board_detector
import helpers
import models
from jobbased import JobBased

root = Pathier(__file__).parent


def num_days(date: datetime) -> int:
    """Returns the number of days since 'date'."""
    return (datetime.now() - date).days


def get_add_parser() -> argshell.ArgShellParser:
    parser = argshell.ArgShellParser(prog="")
    parser.add_argument("position", type=str, help=" The job title of the listing. ")
    parser.add_argument("company", type=str, help=" The company the listing is for. ")
    parser.add_argument("url", type=str, help=" The url of the listing. ")
    parser.add_argument(
        "-l",
        "--location",
        type=str,
        default="Remote",
        help=""" The location of the listing. Defaults to "Remote". """,
    )
    parser.add_argument(
        "-a", "--applied", action="store_true", help=" Mark this listing as 'applied'. "
    )
    return parser


def get_add_board_parser() -> argshell.ArgShellParser:
    parser = argshell.ArgShellParser()
    parser.add_argument("url", type=str, help=" Job board url.3 ")
    parser.add_argument(
        "company",
        type=str,
        help=" Company name. ",
    )
    parser.add_argument(
        "-b",
        "--board_type",
        type=str,
        default=None,
        help=" Specify a board type instead of trying to detect one. ",
    )
    return parser


class JobShell(DBShell):
    _dbpath = Pathier("jobs.db")
    intro = "Starting job_manager (enter help or ? for command info)..."
    prompt = "jobshell>"

    @argshell.with_parser(get_add_board_parser)
    def do_add_scraper(self, args: argshell.Namespace):
        """Add a scraper to the list."""
        with JobBased(self.dbpath) as db:
            args.url = args.url.strip("/")
            db.add_board(args.url, args.company)
            helpers.create_scraper_from_template(
                args.url, args.company, args.board_type
            )

    @argshell.with_parser(get_add_parser)
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

    def do_detect_boards(self, args: str):
        """Try to detect job board url from a company website jobs url and a company name.
        >>> detect_boardtype https://somecompany.com/careers Some Company"""
        (url, company) = args.split(maxsplit=1)
        board_urls = board_detector.get_board_url(company, url)
        if board_urls:
            print(*board_urls, sep="\n")
        else:
            board_type = board_detector.get_board_type_from_page(url)
            if board_type:
                print(
                    f"Could not determine board url, but the board type is <{board_type}>."
                )
            else:
                print("Could not determine 3rd party board information.")

    def do_detect_board_type(self, url: str):
        """Given a company jobs url, try to detect board type."""
        print(board_detector.get_board_type_from_page(url))

    def do_try_boards(self, company: str):
        """Just try all template urls and see what sticks given a company name."""
        urls = board_detector.get_board_by_trial_and_error(company)
        if urls:
            print(*urls, sep="\n")
        else:
            print(urls)

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

    def do_reset_alive_status(self, listing_ids: str):
        """Reset the status of a listing to alive given a list of `listing_id`s."""
        with JobBased(self.dbpath) as db:
            for id_ in listing_ids.split():
                db.reset_alive_status(int(id_))

    def do_trouble_shoot(self, file_stem: str):
        """Show scraper entry and open {file_stem}.py and {file_stem}.log."""
        self.do_open(file_stem)
        company = file_stem.replace("_", " ")
        with JobBased(self.dbpath) as db:
            self.display(db.select("scrapers", where=f"company LIKE '{company}'"))
        os.system(f"code scrapers/{file_stem}.py -r")
        os.system(f"code logs/{file_stem}.log -r")

    def do_find_careers_page(self, base_url: str):
        """Try to find the careers page given a company's base url."""
        urls = board_detector.brute_force_careers_page(base_url)
        if urls:
            print(*urls, sep="\n")
        else:
            print("Valid urls not found.")

    def do_open(self, company: str):
        """Open the board url associated with the given company."""
        with JobBased() as db:
            url = db.get_board(company).url
        webbrowser.open_new_tab(url)

    def preloop(self):
        """Set any applications older than 30 days to rejected."""
        super().preloop()
        with JobBased(self.dbpath) as db:
            db.mark_applications_older_than_30days_as_rejected()


if __name__ == "__main__":
    JobShell().cmdloop()
