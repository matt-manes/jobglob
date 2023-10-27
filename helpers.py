import os
from datetime import datetime
from typing import Generator

import loggi
import loggi.models
from pathier import Pathier

import board_detector
import models

root = Pathier(__file__).parent


def create_scraper_from_template(url: str, company: str, board_type: str | None = None):
    templates_path = root / "templates"
    if not board_type:
        board_type = board_detector.get_board_type_from_text(url)
    if not board_type:
        template = (templates_path / "template.py").read_text()
    else:
        if board_type == "greenhouse_embed":
            board_type = "greenhouse"
        template = (
            (templates_path / "subgruel_template.py")
            .read_text()
            .replace("JobGruel", f"{board_type.capitalize()}Gruel")
        )
    stem = company.lower().replace(" ", "_")
    py_path = root / "scrapers" / f"{stem}.py"
    py_path.write_text(template)
    if not board_type:
        os.system(f"code -r {py_path}")


def load_log(company: str) -> loggi.models.Log:
    stem = company.lower().replace(" ", "_")
    return loggi.load_log(root / "gruel_logs" / f"{stem}.log")


def get_all_logs() -> Generator[loggi.models.Log, None, None]:
    for file in (root / "gruel_logs").glob("*.log"):
        yield loggi.load_log(file)


def get_failed_scrapers(start_time: datetime) -> list[str]:
    """Returns a list of scrapers whose last log message is an `ERROR` or `EXCEPTION`."""
    fails = []
    for log in get_all_logs():
        if log.filter_dates(start_time).filter_levels(["ERROR", "EXCEPTION"]).events:
            assert log.path
            fails.append(log.path.stem)
    return fails


def get_scrapers_with_errors(start_time: datetime) -> dict[str, list[str]]:
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
            log.filter_levels(["WARNING"])
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


def main():
    """ """
    create_scraper_from_template(
        "https://boards.greenhouse.io/kaiahealth", "Kaia Health"
    )


if __name__ == "__main__":
    main()
