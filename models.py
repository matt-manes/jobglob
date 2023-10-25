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
    alive: bool = True
    date_added: datetime = datetime.now()
    date_removed: datetime | None = None

    def __post_init__(self):
        self.alive = bool(self.alive)


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


@dataclass
class Event:
    level: str
    date: datetime
    message: str


@dataclass
class Log:
    events: list[Event]
    path: Pathier | None = None

    def filter_dates(
        self,
        start: datetime = datetime.fromtimestamp(0),
        stop: datetime | None = None,
    ) -> Self:
        if not stop:
            stop = datetime.now()
        return Log(
            [event for event in self.events if start <= event.date <= stop], self.path
        )

    def filter_levels(self, levels: list[str]) -> Self:
        return Log([event for event in self.events if event.level in levels], self.path)

    def filter_messages(
        self, include_patterns: list[str] = ["*"], exclude_patterns: list[str] = []
    ):
        return Log(
            [
                event
                for event in self.events
                if event.message
                in younotyou([event.message], include_patterns, exclude_patterns)
            ],
            self.path,
        )

    def __add__(self, log: Self) -> Self:
        return Log(self.events + log.events)

    def chronosort(self):
        """Sort events by date."""
        self.events = sorted(self.events, key=lambda event: event.date)

    @property
    def last_completion_event(self) -> Event:
        log = self.filter_levels(["INFO"])
        log = log.filter_messages(["*Scrape completed*"])
        return log.events[-1]

    @property
    def last_success_count(self) -> int | None:
        event = self.last_completion_event
        hits = re.findall(r"([0-9]+) successes", event.message)
        if not hits:
            return None
        return int(hits[0][0])

    @property
    def last_fail_count(self) -> int | None:
        event = self.last_completion_event
        hits = re.findall(r"([0-9]+) failures", event.message)
        if not hits:
            return None
        return int(hits[0][0])

    @staticmethod
    def _separate_log(log: str) -> list[str]:
        events = []
        event = ""
        for line in log.splitlines(True):
            if re.findall(r"[A-Z]+\|\-\|", line):
                if event:
                    events.append(event.strip("\n"))
                event = line
            else:
                event += line
        if event:
            events.append(event.strip("\n"))
        return events

    @staticmethod
    def _parse_log(events: list[str]) -> list[Event]:
        sep = "|-|"
        to_datetime = lambda date: datetime.strptime(date, "%m/%d/%Y %I:%M:%S %p")
        logs = []
        for event in events:
            level, date, message = event.split(sep, maxsplit=3)
            logs.append(Event(level, to_datetime(date), message))
        return logs

    @classmethod
    def get_log(cls, company: str) -> Self:
        company = company.lower().replace(" ", "_")
        log_path = root / "logs" / f"{company}.log"
        events = cls._separate_log(log_path.read_text(encoding="utf-8"))
        return cls(cls._parse_log(events), log_path)
