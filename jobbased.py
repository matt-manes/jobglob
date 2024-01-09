from datetime import datetime

from databased import Databased
from pathier import Pathier, Pathish

import models

root = Pathier(__file__).parent


class JobBased(Databased):
    """Database interface for `jobs.db`."""

    def __init__(self, dbpath: Pathish = "jobs.db", *args, **kwargs):
        super().__init__(dbpath, *args, **kwargs)

    @property
    def applications(self) -> list[models.Application]:
        """A list of `models.Application` objects from the database."""
        applied_listings = self._get_listings(
            "listing_id IN (SELECT listing_id FROM applications)", "listing_id"
        )
        return [
            models.Application(listing, datum["application_id"], datum["date_applied"])
            for datum, listing in zip(
                self.select(
                    "applications",
                    ["application_id", "date_applied"],
                    order_by="listing_id",
                ),
                applied_listings,
            )
        ]

    @property
    def boards(self) -> list[models.Board]:
        """A list of `models.Board` objects from the database."""
        data = self.select(
            "boards",
            [
                "board_id",
                "url",
                "boards.date_added AS b_date",
                "boards.company_id",
                "name",
                "companies.date_added AS c_date",
                "active",
            ],
            ["INNER JOIN companies ON boards.company_id = companies.company_id"],
        )
        return [
            models.Board(
                models.Company(datum["company_id"], datum["name"], datum["c_date"]),
                datum["board_id"],
                datum["url"],
                datum["active"],
                datum["b_date"],
            )
            for datum in data
        ]

    @property
    def companies(self) -> list[models.Company]:
        """A list of `models.Company` objects from the database."""
        companies = self.select("companies", ["company_id", "name", "date_added"])
        return [
            models.Company(
                company["company_id"], company["name"], company["date_added"]
            )
            for company in companies
        ]

    @property
    def company_names(self) -> list[str]:
        """A list of company names from the database."""
        return [company.name for company in self.companies]

    @property
    def dead_listings(self) -> list[models.Listing]:
        """A list of dead listings from the database."""
        return self._get_listings("alive = 0")

    @property
    def inactive_boards(self) -> list[models.Board]:
        """A list of boards that have been deactivated (no longer scraped)."""
        return [board for board in self.boards if not board.active]

    @property
    def listings(self) -> list[models.Listing]:
        """A list of `models.Listing` objects from the database."""
        return self._get_listings()

    @property
    def live_applications(self) -> list[models.Application]:
        """A list of applied for positions where the listing is still up."""
        return [app for app in self.applications if app.listing.alive]

    @property
    def live_listings(self) -> list[models.Listing]:
        """A list of job listings that are still up."""
        return self._get_listings("alive = 1")

    @property
    def pinned_dead_listings(self) -> list[models.Listing]:
        """A list of pinned listings that have been taken down."""
        return self._get_listings(
            "alive = 0 AND listing_id IN (SELECT listing_id FROM pinned_listings)"
        )

    @property
    def pinned_listings(self) -> list[models.Listing]:
        """A list of pinned listings."""
        return self._get_listings(
            "listing_id IN (SELECT listing_id FROM pinned_listings)"
        )

    @property
    def pinned_live_listings(self) -> list[models.Listing]:
        """A list of pinned listings that are still up."""
        return self._get_listings(
            "alive = 1 AND listing_id IN (SELECT listing_id FROM pinned_listings)"
        )

    @property
    def rejections(self) -> list[models.Rejection]:
        """A list of rejected applications."""
        rejections = self.select("rejections", order_by="application_id")
        ids = [rejection["application_id"] for rejection in rejections]
        apps = [app for app in self.applications if app.id_ in ids]
        return [
            models.Rejection(app, row["rejection_id"], row["date_rejected"])
            for app, row in zip(apps, rejections)
        ]

    @property
    def unseen_listings(self) -> list[models.Listing]:
        """Listings that haven't been viewed."""
        return self._get_listings(
            "listing_id NOT IN (SELECT listing_id FROM seen_listings)"
        )

    @property
    def unseen_live_listings(self) -> list[models.Listing]:
        """Listings that haven't been viewed and are still up."""
        return self._get_listings(
            "alive = 1 AND listing_id NOT IN (SELECT listing_id FROM seen_listings)"
        )

    def _get_listings(
        self, where: str = "1=1", order_by: str | None = None
    ) -> list[models.Listing]:
        """Returns `model.Listing` objects satisfying the given `where` clause."""
        data = self.select(
            "listings",
            [
                "listing_id AS l_id",
                "position",
                "location",
                "url",
                "scraped_url",
                "companies.company_id AS c_id",
                "name",
                "listings.date_added AS l_date",
                "companies.date_added AS c_date",
                "date_removed",
                "alive",
            ],
            ["INNER JOIN companies ON listings.company_id = companies.company_id"],
            where=where,
            order_by=order_by,
        )
        return [
            models.Listing(
                models.Company(datum["c_id"], datum["name"], datum["c_date"]),
                datum["l_id"],
                datum["position"],
                datum["location"],
                datum["url"],
                datum["scraped_url"],
                datum["alive"],
                datum["l_date"],
                datum["date_removed"],
            )
            for datum in data
        ]

    def add_application(self, listing_id: int):
        """Add `listing_id` to `applications` table."""
        self.insert(
            "applications",
            ("listing_id", "date_applied"),
            [(listing_id, datetime.now())],
        )

    def add_board(self, board_url: str, company: str):
        """Add `board_url` to `boards` table.

        Adds `company` to `companies` table if it isn't already."""
        board_url = board_url.strip("/")
        self.add_company(company)
        company_id = None
        for company_ in self.companies:
            if company_.name == company:
                company_id = company_.id_
                break
        if not company_id:
            raise RuntimeError(
                f"Could not retrieve a `company_id` for {company} when trying to add board."
            )
        self.insert(
            "boards",
            ("url", "company_id", "date_added", "active"),
            [(board_url, company_id, datetime.now(), 1)],
        )

    def add_company(self, name: str):
        """Adds `name` to `companies` table."""
        if name not in self.company_names:
            self.insert("companies", ("name", "date_added"), [(name, datetime.now())])

    def add_listing(self, listing: models.Listing):
        """Add `listing` to the `listings` table."""
        self.insert(
            "listings",
            ("position", "location", "url", "scraped_url", "company_id", "date_added"),
            [
                (
                    listing.position,
                    listing.location,
                    listing.url,
                    listing.scraped_url,
                    listing.company.id_,
                    listing.date_added,
                )
            ],
        )

    def get_board(self, company_name_stem: str) -> models.Board:
        """Returns a `model.Board` object from `company_name_stem`.

        Primarily used for getting `models.Board` using a scraper's file name."""
        name = company_name_stem.replace("_", " ")
        for board in self.boards:
            if board.company.name.lower() == name:
                return board
        raise ValueError(
            f"Could not retrieve a board for company stem `{company_name_stem}`"
        )

    def get_company_from_name(self, company_name: str) -> models.Company | None:
        """Returns a `models.Company` object from `company_name` (case insensitive) if it exists."""
        try:
            company = self.select("companies", where=f"name LIKE '{company_name}'")[0]
        except Exception as e:
            return None
        return models.Company(
            company["company_id"], company["name"], company["date_added"]
        )

    def mark_applications_older_than_30days_as_rejected(self):
        """Mark any applications older than 30 days as rejected."""
        rejected_application_ids = [
            rejection.application.id_ for rejection in self.rejections
        ]
        for application in self.applications:
            if (
                application.id_ not in rejected_application_ids
                and (datetime.now() - application.date_applied).days > 30
            ):
                print(
                    f"Marking application #{application.id_} for listing '{application.listing.id_}. {application.listing.position} -- {application.listing.company.name}' as rejected."
                )
                self.mark_rejected(application.id_)

    def mark_dead(self, listing_id: int):
        """Mark listing with `listing_id` as dead."""
        self.update("listings", "alive", 0, f"listing_id = {listing_id}")
        self.update(
            "listings", "date_removed", datetime.now(), f"listing_id = {listing_id}"
        )

    def mark_rejected(self, application_id: int):
        """Add `application_id` to `rejections` table."""
        self.insert(
            "rejections",
            ("application_id", "date_rejected"),
            [(application_id, datetime.now())],
        )

    def mark_seen(self, listing_id: int):
        """Add `listing_id` to `seen_listings` table."""
        self.insert("seen_listings", ("listing_id",), [(listing_id,)])

    def pin_listing(self, listing_id: int):
        """Add `listing_id` to `pinned_listings` table."""
        self.insert("pinned_listings", ("listing_id",), [(listing_id,)])

    def reset_alive_status(self, listing_id: int):
        """Update a listing's `alive` column to `1` and `date_removed` column to `NULL`."""
        self.update("listings", "alive", 1, f"listing_id = {listing_id}")
        self.query(
            f"UPDATE listings SET date_removed = NULL WHERE listing_id = {listing_id};"
        )

    def to_grid(self, rows: list[dict]) -> str:
        for i, row in enumerate(rows):
            for col in row:
                row[col] = str(row[col])
            rows[i] = row
        return super().to_grid(rows)
