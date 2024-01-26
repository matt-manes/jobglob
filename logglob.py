from datetime import datetime
from typing import Generator

import loggi
from pathier import Pathier, Pathish

import helpers
from config import Config

root = Pathier(__file__).parent
config = Config.load()


def load_log(company: str) -> loggi.models.Log:
    """Returns a `loggi.models.Log` object for the scraper associated with `company`."""
    stem = company.lower().replace(" ", "_")
    return loggi.load_log(config.scraper_logs_dir / f"{stem}.log")


def get_all_logs() -> Generator[loggi.models.Log, None, None]:
    """Generator yielding `loggi.models.Log` objects from `./gruel_logs`."""
    for file in config.scraper_logs_dir.glob("*.log"):
        yield loggi.load_log(file)


def get_failed_scrapers(start_time: datetime) -> list[str]:
    """Returns a list of scrapers whose last log message is an `ERROR` or `EXCEPTION`."""
    fails = []
    for log in get_all_logs():
        if log.filter_dates(start_time).filter_levels(["ERROR", "EXCEPTION"]).events:
            assert log.path
            fails.append(log.path.stem)
    return fails


def get_resurrected_listings_count(start_time: datetime) -> int:
    """Returns the number of resurrected listings logged since `start_time`."""
    count = 0
    for log in get_all_logs():
        # message = 'Resurrected x listings.'
        log = log.filter_dates(start_time).filter_messages(["Resurrected*"])
        if log.events:
            count += int(log.events[-1].message.split()[1])
    return count


def get_scrapers_with_errors(start_time: datetime) -> dict[str, list[str]]:
    """Returns scrapers that have errors after `start_time`.

    Ouput is a dictionary where the error type is the key and the values are lists of scrapers.

    Error keys: `redirects`, `404s`, `no_listings`, `parse_fails`, and `misc_fails`."""
    scrapers = {
        "redirects": [],
        "404s": [],
        "no_listings": [],
        "parse_fails": [],
        "misc_fails": [],
    }
    for log in get_all_logs():
        log = log.filter_dates(start_time)
        assert log.path
        error_exceptions = log.filter_levels(["ERROR", "EXCEPTION"])
        if (
            log.filter_levels(["WARNING", "EXCEPTION"])
            .filter_messages(["Board url * resolved to *"])
            .events
        ):
            scrapers["redirects"].append(log.path.stem)
        elif error_exceptions.filter_messages(["*returned status code 404*"]).events:
            scrapers["404s"].append(log.path.stem)
        elif log.filter_messages(["*get_parsable_items() returned 0 items*"]).events:
            scrapers["no_listings"].append(log.path.stem)
        elif error_exceptions.filter_messages(["*Failure to parse item*"]).events:
            scrapers["parse_fails"].append(log.path.stem)
        elif error_exceptions.events:
            scrapers["misc_fails"].append(log.path.stem)
    return scrapers
