from databased import DBShell, dbparsers, DataBased
from datetime import datetime
import argshell
import os
import time
from pathier import Pathier

root = Pathier(__file__).parent


def num_days(date: datetime) -> datetime:
    """Returns the number of days since 'date'."""
    return (datetime.now() - date).days


def get_add_parser() -> argshell.Namespace:
    parser = argshell.ArgShellParser(prog="")
    parser.add_argument("name", type=str, help=""" The job title of the listing. """)
    parser.add_argument(
        "company", type=str, help=""" The company the listing is for. """
    )
    parser.add_argument("url", type=str, help=""" The url of the listing. """)
    parser.add_argument(
        "xpath",
        type=str,
        help=""" An xpath to use when determining if the listing is still up. """,
    )
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


class JobManager(DBShell):
    intro = "Starting job_manager (enter help or ? for command info)..."
    prompt = "jobshell>"
    dbpath = "joblistings.db"  # Replace None with a path to a .db file to set a default database

    def do_alive(self, arg: str):
        """Show listings that are still up."""
        with DataBased(self.dbpath) as db:
            rows = db.get_rows(
                "listings",
                [("alive", 1)],
                columns_to_return=[
                    "name",
                    "company",
                    "url",
                    "applied",
                    "rejected",
                    "date_added",
                ],
                order_by="date_added desc",
            )
        for row in rows:
            date_added = row.pop("date_added")
            row["days_since_adding"] = num_days(date_added)
        print(DataBased.data_to_string(rows))

    def do_dead(self, arg: str):
        """Show listings that are no longer up."""
        with DataBased(self.dbpath) as db:
            rows = db.get_rows(
                "listings",
                [("alive", 0)],
                columns_to_return=[
                    "name",
                    "company",
                    "url",
                    "applied",
                    "rejected",
                    "date_added",
                ],
                order_by="date_added desc",
            )
        for row in rows:
            date_added = row.pop("date_added")
            row["days_since_adding"] = num_days(date_added)
        print(DataBased.data_to_string(rows))

    def do_applied(self, arg: str):
        """Show listings you applied for."""
        with DataBased(self.dbpath) as db:
            rows = db.get_rows(
                "listings",
                [("applied", 1)],
                # sort_by_column="alive",
                columns_to_return=[
                    "name",
                    "company",
                    "url",
                    "alive",
                    "rejected",
                    "date_applied",
                    "date_rejected",
                ],
                order_by="rejected",
            )
            rejected_rows = sorted(
                [row for row in rows if row["rejected"]],
                key=lambda r: r["date_applied"],
                reverse=True,
            )
            not_yet_rejected_rows = sorted(
                [row for row in rows if not row["rejected"]],
                key=lambda r: r["date_applied"],
                reverse=True,
            )
            rows = not_yet_rejected_rows + rejected_rows

            for row in rows:
                date_applied = row.pop("date_applied")
                row["days_since_applying"] = (datetime.now() - date_applied).days
                date_rejected = row.pop("date_rejected")
                if date_rejected:
                    row["days_since_rejection"] = (datetime.now() - date_rejected).days
                else:
                    row["days_since_rejection"] = None
        grid = DataBased.data_to_string(rows)
        print(grid)
        print(f"Not yet rejected listings: {len(not_yet_rejected_rows)}")
        print(f"Rejected listings: {len(rejected_rows)}")
        print(
            f"Applications in past 7 days: {len([row for row in rows if int(row['days_since_applying']) <= 7])}"
        )
        print(f"Total applications: {len(rows)}")

    def do_rejected(self, arg: str):
        """Show rejected applications."""
        with DataBased(self.dbpath) as db:
            rows = db.get_rows(
                "listings",
                {"rejected": 1},
                order_by="date_rejected desc",
                columns_to_return=[
                    "name",
                    "company",
                    "url",
                    "alive",
                    "date_applied",
                    "date_rejected",
                ],
            )
            for row in rows:
                date_applied = row.pop("date_applied")
                row["days_since_applying"] = num_days(date_applied)
                date_rejected = row.pop("date_rejected")
                row["days_since_rejection"] = num_days(date_rejected)
            print(DataBased.data_to_string(rows))

    @argshell.with_parser(get_add_parser)
    def do_add_listing(self, args: argshell.Namespace):
        """Add a job listing to the database."""
        with DataBased(self.dbpath) as db:
            db.add_row(
                "listings",
                (
                    args.name,
                    args.company,
                    args.url,
                    int(args.applied),
                    1,
                    args.xpath,
                    datetime.now(),
                    datetime.now() if args.applied else None,
                    None,
                    args.found_on,
                    0,
                    None,
                ),
            )

    def do_mark_applied(self, arg: str):
        """Mark a job as applied.
        The argument expected is the url of the listing."""
        with DataBased(self.dbpath) as db:
            db.update("listings", "applied", 1, {"url": arg})
            db.update("listings", "date_applied", datetime.now(), {"url": arg})

    def do_mark_rejected(self, arg: str):
        """Mark a job as rejected.
        The argument expected is the url of the listing."""
        with DataBased(self.dbpath) as db:
            db.update("listings", "rejected", 1, {"url": arg})
            db.update("listings", "date_rejected", datetime.now(), {"url": arg})

    def do_open(self, arg: str):
        """Open job boards in browser."""
        last_check_path = root / "lastcheck.toml"
        last_check = last_check_path.loads()["time"]
        current_time = time.time()
        delta = int((current_time - last_check) / (3600 * 24))
        print(f"Boards last checked {delta} days ago.")
        last_check_path.dumps({"time": current_time})
        os.system("open.py")

    def do_reset_alive_status(self, args: str):
        """Reset the status of a listing to alive.

        :params:

        `args`: A list of urls to reset.
        """
        urls = args.split()
        with DataBased(self.dbpath) as db:
            for url in urls:
                db.update("listings", "alive", 1, {"url": url})
                db.query(
                    f'UPDATE listings SET date_removed = NULL where url = "{url}";'
                )

    def do_add_to_boards(self, args: str):
        """Add a list of urls to `jobBoards.txt`."""
        urls = args.split()
        path = root / "jobBoards.txt"
        boards = path.split()
        [boards.insert(-1, url) for url in urls]
        path.join(boards)

    def do_remove_from_boards(self, args: str):
        """Remove a list of urls from `jobBoards.txt`."""
        urls = args.split()
        path = root / "jobBoards.txt"
        boards = path.split()
        [boards.pop(boards.index(url)) for url in urls]
        path.join(boards)

    def do_update_xpath(self, args: str):
        """Give a url and a new xpath."""
        args = args.strip()
        url, xpath = args[: args.find(" ")], args[args.find(" ") + 1 :]
        with DataBased(self.dbpath) as db:
            db.update("listings", "xpath", xpath, {"url": url})

    def preloop(self):
        """Set any applications older than 30 days to rejected."""
        super().preloop()
        with DataBased(self.dbpath) as db:
            rows = db.get_rows("listings", {"applied": 1, "rejected": 0})
            for row in rows:
                if num_days(row["date_applied"]) > 30:
                    matcher = [("url", row["url"])]
                    db.update("listings", "rejected", 1, matcher)
                    db.update("listings", "date_rejected", datetime.now(), matcher)


if __name__ == "__main__":
    JobManager().cmdloop()
