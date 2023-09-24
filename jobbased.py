from databased import Databased
from pathier import Pathier, Pathish
from datetime import datetime

root = Pathier(__file__).parent


class JobBased(Databased):
    def __init__(self, dbpath: Pathish = "jobs.db", *args, **kwargs):
        super().__init__(dbpath, *args, **kwargs)

    @property
    def applications(self) -> list[dict]:
        return self.select("applications")

    @property
    def boards(self) -> list[str]:
        return [row["url"] for row in self.select("boards", ["url"])]

    @property
    def companies(self) -> list[str]:
        return [row["name"] for row in self.select("companies", ["name"])]

    @property
    def dead_listings(self) -> list[dict]:
        return self.select("listings", where="alive = 0")

    @property
    def live_applications(self) -> list[dict]:
        return self.select("applications", where="rejected = 0")

    @property
    def live_listings(self) -> list[dict]:
        return self.select("listings", where="alive = 1")

    @property
    def rejected_applications(self) -> list[dict]:
        return self.select("applications", where="rejected = 1")

    def add_application(self, listing_id: int, cover_letter: bool = False):
        self.insert(
            "applications",
            ("listing_id", "date_applied", "wrote_cover_letter"),
            [(listing_id, datetime.now(), int(cover_letter))],
        )

    def add_board(self, url: str, company: str | None = None):
        url = url.strip("/")
        self.insert("boards", ("url", "date_added"), [(url, datetime.now())])
        if company and company in self.companies:
            board_id = self.query(f"SELECT board_id FROM boards WHERE url='{url}';")[0][
                0
            ]
            board_id = self.select("boards", ["board_id"], where=f"url = '{url}'")[0][
                "board_id"
            ]
            self.update("companies", "board_id", board_id, f"company = '{company}'")

    def add_listing(
        self,
        position: str,
        company: str,
        url: str,
        xpath: str,
        found_on: str | None = None,
    ):
        if company not in self.companies:
            self.insert(
                "companies", ("name", "date_added"), [(company, datetime.now())]
            )
        company_id = self.select(
            "companies", ["company_id"], where=f"name = '{company}'"
        )[0]["company_id"]
        self.insert(
            "listings",
            ("name", "company_id", "url", "xpath", "found_on", "date_added"),
            [(position, company_id, url, xpath, found_on, datetime.now())],
        )

    def create_schema(self, path: Pathish = "schema.sql"):
        self.execute_script(path)

    def mark_applications_older_than_30days_as_rejected(self):
        for application in self.live_applications:
            if (datetime.now() - application["date_applied"]).days > 30:
                listing = self.select(
                    "listings",
                    ["listing_id", "position", "companies.name AS company"],
                    [
                        "INNER JOIN companies ON listings.company_id=companies.company_id"
                    ],
                    where=f"listing_id = '{application['listing_id']}';",
                )[0]
                print(
                    f"Marking application for '{listing['listing_id']}. {listing['position']} -- {listing['company']}' as rejected."
                )
                self.mark_rejected(application["application_id"])

    def mark_rejected(self, application_id: int):
        for datum in [("rejected", 1), ("date_rejected", datetime.now())]:
            self.update(
                "applications", datum[0], datum[1], f"application_id = {application_id}"
            )

    def mark_dead(self, listing_id: int):
        self.update("listings", "alive", 0, f"listing_id = {listing_id}")
        self.update(
            "listings", "date_removed", datetime.now(), f"listing_id = {listing_id}"
        )

    def remove_board(self, url: str):
        url = url.strip("/")
        board_id = self.select("boards", ["board_id"], where=f"url = '{url}'")[0][
            "board_id"
        ]
        if self.select("companies", where=f"board_id = {board_id}"):
            self.update("companies", "board_id", None, f"board_id = {board_id}")
        self.delete("boards", f"board_id = {board_id}")

    def reset_alive_status(self, url: str):
        self.update("listings", "alive", 1, f"url = '{url}'")
        self.query(f"UPDATE listings SET date_removed = NULL WHERE url = '{url}';")

    def to_grid(self, rows: list[dict]) -> str:
        for i, row in enumerate(rows):
            for col in row:
                row[col] = str(row[col])
            rows[i] = row
        return super().to_grid(rows)


if __name__ == "__main__":
    with JobBased() as db:
        print(db.boards)
