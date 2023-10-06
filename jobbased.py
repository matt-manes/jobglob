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
    def scrapable_boards(self) -> list[str]:
        return [row["url"] for row in self.select("scrapable_boards", ["url"])]

    @property
    def scraped_listings_urls(self) -> list[str]:
        return [row["url"] for row in self.select("scraped_listings", ["url"])]

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

    @property
    def unseen_listings(self) -> list[dict]:
        return self.select(
            "scraped_listings",
            [
                "listing_id AS id",
                "position",
                "companies.name AS company",
                "location",
                "scraped_listings.url",
            ],
            [
                "INNER JOIN companies ON scraped_listings.company_id = companies.company_id"
            ],
            where="seen = 0 AND alive = 1",
        )

    def mark_seen(self, listing_id: int):
        self.update("scraped_listings", "seen", 1, f"listing_id = {listing_id}")

    def mark_intrested(self, listing_id: int, xpath: str):
        listing = self.select("scraped_listings", where=f"listing_id = {listing_id}")[0]
        self.insert(
            "listings",
            ("position", "company_id", "url", "xpath", "date_added"),
            [
                (
                    listing["position"],
                    listing["company_id"],
                    listing["url"],
                    xpath,
                    datetime.now(),
                )
            ],
        )

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
            board_id = self.select("boards", ["board_id"], where=f"url = '{url}'")[0][
                "board_id"
            ]
            self.update("companies", "board_id", board_id, f"name = '{company}'")

    def add_scrapable_board(self, url: str, company: str):
        url = url.strip("/")
        self.insert("scrapable_boards", ("url", "date_added"), [(url, datetime.now())])
        self.add_company(company)
        board_id = self.select(
            "scrapable_boards", ["board_id"], where=f"url = '{url}'"
        )[0]["board_id"]
        self.update("companies", "board_id", board_id, f"name = '{company}'")

    def add_company(self, name: str):
        if name not in self.companies:
            self.insert("companies", ("name", "date_added"), [(name, datetime.now())])

    def get_company_id(self, name: str) -> int:
        return self.select("companies", ["company_id"], where=f"name = '{name}'")[0][
            "company_id"
        ]

    def get_scrapable_board_url(self, name: str) -> str:
        return self.select(
            "companies",
            ["scrapable_boards.url"],
            [
                "INNER JOIN scrapable_boards ON companies.board_id=scrapable_boards.board_id"
            ],
            where=f"companies.name LIKE '{name.replace('_', ' ')}'",
        )[0]["url"]

    def get_scrapable_board_company(self, name: str) -> str:
        return self.select(
            "companies",
            ["name"],
            where=f"companies.name LIKE '{name.replace('_', ' ')}'",
        )[0]["name"]

    def add_listing(
        self,
        position: str,
        company: str,
        url: str,
        xpath: str,
        found_on: str | None = None,
    ):
        self.add_company(company)
        company_id = self.get_company_id(company)
        self.insert(
            "listings",
            ("position", "company_id", "url", "xpath", "found_on", "date_added"),
            [(position, company_id, url, xpath, found_on, datetime.now())],
        )

    def add_scraped_listing(self, position: str, location: str, url: str, company: str):
        self.add_company(company)
        company_id = self.get_company_id(company)
        self.insert(
            "scraped_listings",
            ("position", "location", "url", "company_id", "date_added"),
            [(position, location, url, company_id, datetime.now())],
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
