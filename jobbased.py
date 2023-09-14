from databased import DataBased, _connect
from pathier import Pathier, Pathish
from datetime import datetime

root = Pathier(__file__).parent


class JobBased(DataBased):
    def __init__(self, dbpath: Pathish = "jobs.db", *args, **kwargs):
        super().__init__(dbpath, *args, **kwargs)

    @property
    def applications(self) -> list[dict]:
        return self.get_rows("applications")

    @property
    def boards(self) -> list[str]:
        return [
            row[0]
            for row in self.get_rows(
                "boards", columns_to_return=["url"], values_only=True
            )
        ]

    @property
    def companies(self) -> list[str]:
        return [
            row[0]
            for row in self.get_rows(
                "companies", columns_to_return=["name"], values_only=True
            )
        ]

    @property
    def dead_listings(self) -> list[dict]:
        return self.get_rows("listings", {"alive": 0})

    @property
    def live_applications(self) -> list[dict]:
        return self.get_rows("applications", {"rejected": 0})

    @property
    def live_listings(self) -> list[dict]:
        return self.get_rows("listings", {"alive": 1})

    @property
    def rejected_applications(self) -> list[dict]:
        return self.get_rows("applications", {"rejected": 1})

    def add_application(self, url: str, cover_letter: bool = False):
        listing_id = self.query(f"SELECT listing_id FROM listings WHERE url='{url}';")[
            0
        ][0]
        self.add_row(
            "applications",
            (listing_id, datetime.now(), int(cover_letter)),
            ("listing_id", "date_applied", "wrote_cover_letter"),
        )

    def add_board(self, url: str, company: str | None = None):
        url = url.strip("/")
        self.add_row("boards", (url, datetime.now()), ("url", "date_added"))
        if company and company in self.companies:
            board_id = self.query(f"SELECT board_id FROM boards WHERE url='{url}';")[0][
                0
            ]
            self.update("companies", "board_id", board_id, {"company": company})

    def add_listing(
        self, position: str, company: str, url: str, xpath: str, found_on: str = None
    ):
        if company not in self.companies:
            self.add_row("companies", (company, datetime.now()), ("name", "date_added"))
        company_id = self.query(
            f"SELECT company_id FROM companies WHERE name='{company}';"
        )[0][0]
        self.add_row(
            "listings",
            (position, company_id, url, xpath, found_on, datetime.now()),
            ("name", "company_id", "url", "xpath", "found_on", "date_added"),
        )

    def create_schema(self, path: Pathish = "schema.sql"):
        self.open()
        self.connection.executescript(Pathier(path).read_text())

    @_connect
    def execute_script(self, path: Pathish) -> list[tuple]:
        sql = Pathier(path).read_text().replace("\n", " ")
        return [list(row) for row in self.query(sql)]

    def mark_applications_older_than_30days_as_rejected(self):
        for application in self.live_applications:
            if (datetime.now() - application["date_applied"]).days > 30:
                listing_id, position, company = self.query(
                    f" SELECT listing_id, listings.name, companies.name FROM listings INNER JOIN companies ON listings.company_id=companies.company_id WHERE listing_id='{application['listing_id']}'; "
                )[0]
                print(
                    f"Marking application for '{listing_id}. {position} -- {company}' as rejected."
                )
                self.mark_rejected(application["application_id"])

    def mark_rejected(self, application_id: int):
        for datum in [("rejected", 1), ("date_rejected", datetime.now())]:
            self.update(
                "applications", datum[0], datum[1], {"application_id": application_id}
            )

    def mark_dead(self, listing_id: int):
        self.update("listings", "alive", 0, [("listing_id", listing_id)])
        self.update(
            "listings", "date_removed", datetime.now(), [("listing_id", listing_id)]
        )

    def remove_board(self, url: str):
        url = url.strip("/")
        board_id = self.query(f"SELECT board_id FROM boards WHERE url = '{url}';")[0][0]
        if self.query(f"SELECT * FROM companies WHERE board_id = '{board_id}';"):
            self.update("companies", "board_id", None, {"board_id": board_id})
        self.delete("boards", {"board_id": board_id})

    def reset_alive_status(self, url: str):
        self.update("listings", "alive", 1, {"url": url})
        self.query(f"UPDATE listings SET date_removed = NULL WHERE url = '{url}';")


if __name__ == "__main__":
    with JobBased() as db:
        print(db.boards)
