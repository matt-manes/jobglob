from dataclasses import dataclass
from datetime import datetime

import requests
from pathier import Pathier
from whosyouragent import whosyouragent

root = Pathier(__file__).parent


@dataclass
class Company:
    """
    Fields:
    * id_: int
    * name: str
    * date_added: datetime
    """

    id_: int = -1
    name: str = ""
    date_added: datetime = datetime.now()


@dataclass
class Board:
    """
    Fields:
    * company: models.Company
    * id_: int
    * url: str
    * active: bool
    * date_added: datetime
    """

    company: Company
    id_: int = -1
    url: str = ""
    active: bool = True
    date_added: datetime = datetime.now()


@dataclass
class Listing:
    """
    Fields:
    * company: models.Company
    * id_: int
    * position: str
    * location: str
    * url: str
    * scraped_url: str
    * alive: bool
    * date_added: datetime
    * date_removed: datetime | None
    """

    company: Company
    id_: int = -1
    position: str = ""
    location: str = ""
    url: str = ""
    scraped_url: str = ""
    alive: bool = True
    date_added: datetime = datetime.now()
    date_removed: datetime | None = None

    def __post_init__(self):
        self.alive = bool(self.alive)

    def prune_strings(self):
        """Remove extra whitespaces from `self.position` and `self.location` strings."""
        prune = lambda s: " ".join(s.strip().split())
        self.position = prune(self.position)
        self.location = prune(self.location)

    def resolve_url(self):
        """Check `self.url` for redirection.

        If it redirects, store `self.url` in `self.scraped_url` and store the resolved url in `self.url`.
        """
        response = requests.get(
            self.url, headers={"User-Agent": whosyouragent.get_agent()}, timeout=10
        )
        if response.status_code not in [200, 202, 302]:
            raise RuntimeError(
                f"Error resolving url '{self.url}' for listing '{self.company}: '{self.position}'. Status code: {response.status_code} Resolved url: '{response.url}'"
            )
        resolved_url = response.url.strip("/")
        if resolved_url != self.url.strip("/"):
            self.scraped_url = self.url.strip("/")
            self.url = resolved_url


@dataclass
class Application:
    """
    Fields:
    * listing: models.Listing
    * id_: int
    * date_applied: datetime
    """

    listing: Listing
    id_: int = -1
    date_applied: datetime = datetime.now()


@dataclass
class Rejection:
    """
    Fields:
    * application: Application
    * id_: int
    * date_rejected: datetime
    """

    application: Application
    id_: int = -1
    date_rejected: datetime = datetime.now()


@dataclass
class Scraper:
    """
    Fields:
    * company: models.Company
    * board: models.Board
    """

    company: Company
    board: Board
