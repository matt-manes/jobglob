import re
from dataclasses import dataclass
from datetime import datetime

from pathier import Pathier
from typing_extensions import Self
from younotyou import younotyou

root = Pathier(__file__).parent


@dataclass
class Company:
    id_: int = -1
    name: str = ""
    date_added: datetime = datetime.now()


@dataclass
class Board:
    company: Company
    id_: int = -1
    url: str = ""
    date_added: datetime = datetime.now()


@dataclass
class Listing:
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
        prune = lambda s: " ".join(s.strip().split())
        self.position = prune(self.position)
        self.location = prune(self.location)


@dataclass
class Application:
    listing: Listing
    id_: int = -1
    date_applied: datetime = datetime.now()


@dataclass
class Rejection:
    application: Application
    id_: int = -1
    date_rejected: datetime = datetime.now()


@dataclass
class Scraper:
    company: Company
    board: Board
