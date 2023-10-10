from databased import Databased
from databased.dbshell import DBShell
from datetime import datetime
import argshell
import os
import time
from pathier import Pathier
from griddle import griddy
from jobbased import JobBased
import helpers

root = Pathier(__file__).parent


def num_days(date: datetime) -> int:
    """Returns the number of days since 'date'."""
    return (datetime.now() - date).days


def get_add_parser() -> argshell.ArgShellParser:
    parser = argshell.ArgShellParser(prog="")
    parser.add_argument("name", type=str, help=""" The job title of the listing. """)
    parser.add_argument(
        "company", type=str, help=""" The company the listing is for. """
    )
    parser.add_argument("url", type=str, help=""" The url of the listing. """)

    parser.add_argument(
        "-f",
        "--found_on",
        type=str,
        default="",
        help=""" Where the listing was found. """,
    )
    parser.add_argument(
        "-a",
        "--applied",
        action="store_true",
        help=""" Mark this listing as 'applied'. """,
    )
    return parser


def get_add_board_parser() -> argshell.ArgShellParser:
    parser = argshell.ArgShellParser()
    parser.add_argument("url", type=str, help=""" Job board url """)
    parser.add_argument(
        "company",
        type=str,
        nargs="?",
        default=None,
        help=""" Company name if applicable. """,
    )
    return parser


def get_add_scrapable_board_parser() -> argshell.ArgShellParser:
    parser = get_add_board_parser()
    parser.add_argument(
        "-b",
        "--board_type",
        type=str,
        default=None,
        help=""" Specify a board type instead of trying to detect one. """,
    )
    return parser


class JobShell(DBShell):
    intro = "Starting job_manager (enter help or ? for command info)..."
    prompt = "jobshell>"
    _dbpath = Pathier("jobs.db")

    def do_alive(self, arg: str):
        """Show listings that are still up."""
        with JobBased(self.dbpath) as db:
            rows = db.execute_script("live_listings.sql")
        print(db.to_grid(rows))

    def do_dead(self, arg: str):
        """Show listings that are no longer up."""
        with JobBased(self.dbpath) as db:
            rows = db.execute_script("dead_listings.sql")
        print(db.to_grid(rows))

    def do_applied(self, arg: str):
        """Show listings you applied for."""
        with JobBased(self.dbpath) as db:
            rows = db.execute_script("applications.sql")
            """ for i, row in enumerate(rows):
                rows[i] = ["" if item is None else item for item in row] """
            print(db.to_grid(rows))
            print(f"Not yet rejected: {len(db.live_applications)}")
            print(f"Rejected: {len(db.rejected_applications)}")
            print(f"Total applications: {len(db.applications)}")
            last_seven_days = db.query(
                "SELECT COUNT(*) AS num_applications FROM applications WHERE (JULIANDAY('now')-JULIANDAY(date_applied)) < 7;"
            )[0]["num_applications"]
            print(f"Applications in last 7 days: {last_seven_days}")

    @argshell.with_parser(get_add_parser)
    def do_add_listing(self, args: argshell.Namespace):
        """Add a job listing to the database."""
        with JobBased(self.dbpath) as db:
            db.add_listing(
                args.name, args.company, args.url.strip("/"), "", args.found_on
            )
            if args.applied:
                db.add_application(args.url.strip("/"))

    def do_mark_applied(self, listing_id: str):
        """Mark a job as applied given the `listing_id`."""
        with JobBased(self.dbpath) as db:
            db.add_application(int(listing_id))

    def do_mark_rejected(self, application_id: str):
        """Mark a job as rejected given the `application_id`."""
        with JobBased(self.dbpath) as db:
            db.mark_rejected(int(application_id))

    def do_open(self, arg: str):
        """Open job boards in browser."""
        last_check_path = root / "lastcheck.toml"
        last_check = last_check_path.loads()["time"]
        current_time = time.time()
        delta = int((current_time - last_check) / (3600 * 24))
        print(f"Boards last checked {delta} days ago.")
        last_check_path.dumps({"time": current_time})
        os.system("open_boards.py")

    def do_reset_alive_status(self, args: str):
        """Reset the status of a listing to alive.

        :params:

        `args`: A list of urls to reset.
        """
        urls = args.split()
        with JobBased(self.dbpath) as db:
            for url in urls:
                db.reset_alive_status(url)

    @argshell.with_parser(get_add_board_parser)
    def do_add_board(self, args: argshell.Namespace):
        """Add a url to boards list."""
        with JobBased(self.dbpath) as db:
            args.url = args.url.strip("/")
            if args.url not in db.boards:
                db.add_board(args.url, args.company)

    @argshell.with_parser(get_add_scrapable_board_parser)
    def do_add_scrapable_board(self, args: argshell.Namespace):
        """Add a url to scrapable boards list."""
        if not args.company:
            print("Scrapable boards require a company name.")
        else:
            with JobBased(self.dbpath) as db:
                args.url = args.url.strip("/")
                if args.url not in db.scrapable_boards:
                    db.add_scrapable_board(args.url, args.company)
                    helpers.create_scraper_from_template(
                        args.url, args.company, args.board_type
                    )

    def do_remove_from_boards(self, args: str):
        """Remove a url from boards list."""
        with JobBased(self.dbpath) as db:
            db.remove_board(args)

    def do_delete_scraper(self, board_id: str):
        """Delete a scraper given its `board_id`.
        Deletes the corresponding `scrapable_boards` entry, scraper file, and scraper log file."""
        board_id = int(board_id)  # type: ignore
        print("Delete the following?")
        with JobBased(self.dbpath) as db:
            self.display(
                db.select(
                    "scrapable_boards",
                    [
                        "scrapable_boards.board_id",
                        "scrapable_boards.url",
                        "companies.name",
                    ],
                    [
                        "INNER JOIN companies ON scrapable_boards.board_id = companies.board_id"
                    ],
                    where=f"scrapable_boards.board_id = {board_id}",
                )
            )
        ans = input("y/n: ")
        if ans == "y":
            helpers.delete_scraper(board_id)  # type: ignore

    def do_mark_dead(self, listing_id: str):
        """Given a `listing_id`, mark a listing as removed."""
        with JobBased(self.dbpath) as db:
            db.mark_dead(int(listing_id))

    def do_extract_boardtype(self, url: str):
        print(helpers.extract_board_type(url))

    def preloop(self):
        """Set any applications older than 30 days to rejected."""
        super().preloop()
        with JobBased(self.dbpath) as db:
            db.mark_applications_older_than_30days_as_rejected()


if __name__ == "__main__":
    JobShell().cmdloop()
