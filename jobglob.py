import random
from collections import deque
from datetime import datetime
from types import ModuleType
from typing import Any, Type

import loggi
import quickpool
from gruel import Brewer, Gruel, GruelFinder
from noiftimer import Timer
from pathier import Pathier

import helpers
import jobgruel
import models
from board_detector import BoardDetector
from jobbased import JobBased

root = Pathier(__file__).parent


class ScraperLoader:
    def __init__(self):
        self.board_detector = BoardDetector()
        self.scrapers_path = root / "scrapers"
        self.finder = GruelFinder(log_dir=root / "logs")
        self.logger = loggi.getLogger("scrapeloader", root / "logs")

    def log_class_loaded(self, class_: Type[Any], from_: Any):
        """Log "Loaded `{class_}` from `{from_}`." """
        self.logger.debug(f"Loaded `{class_}` from `{from_}`.")

    def get_class_from_file(self, file: Pathier) -> Type[Gruel] | None:
        """Load and return scraper class defined in `file`."""
        module = self.finder.load_module_from_file(file)
        if not module:
            self.logger.error(f"Could not load `{file}` as a module.")
            return None
        gruel_classes = self.finder.strain_for_gruel([module])
        # =================================================================================
        # When a file does `from jobgruel import {SubGruel}` instead of `import jobgruel`,
        # gruel_classes will likely contain multiple classes:
        # the one defined in the file and the imported one.
        # To load the correct one, choose the one with the most base classes.
        # e.g. A class that inherits from `GreenhouseGruel` will have 3 bases:
        # `GreenhouseGruel`->`JobGruel`->`Gruel`
        # but `GreenhouseGruel` will have 2: `JobGruel`->`Gruel`
        # =================================================================================
        class_ = max(
            gruel_classes, default=None, key=lambda c: len(self.finder.get_bases(c))
        )
        if not class_:
            self.logger.error(f"No `gruel.Gruel` subclasses found in `{file}`.")
        else:
            self.log_class_loaded(class_, file)
        return class_

    def get_class_from_url(self, url: str) -> Type[jobgruel.JobGruel] | None:
        """Load and return a `jobgruel.JobGruel` class according to `board.url`."""
        board_type = self.board_detector.get_board_type_from_text(url)
        if not board_type:
            self.logger.error(f"Could not detect a board type from `{url}`.")
            return None
        if board_type == "greenhouse_embed":
            board_type = "greenhouse"
        class_ = getattr(jobgruel, f"{board_type.capitalize()}Gruel", None)
        if not class_:
            self.logger.error(
                f"No `JobGruel` subclass found for board type `{board_type}` from `{url}`."
            )
        else:
            self.log_class_loaded(class_, url)
        return class_

    def load_active_scrapers(
        self,
    ) -> deque[tuple[models.Board, Type[jobgruel.JobGruel]]]:
        """Get active scrapers from the database and determine their corresponding `JobGruel` subclass.

        Returns a list of tuples where each tuple consists of the board and the class.
        """
        with JobBased() as db:
            boards = db.get_active_boards()
        random.shuffle(boards)
        scrapers = deque()
        for board in boards:
            stem = helpers.name_to_stem(board.company.name)
            file = self.scrapers_path / f"{stem}.py"
            scraper_class = (
                self.get_class_from_file(file)
                if file.exists()
                else self.get_class_from_url(board.url)
            )
            if scraper_class:
                scrapers.append((board, scraper_class))
            else:
                self.logger.error(f"No scraper class found for `{board}`.")
        return scrapers


class JobGlob(Brewer):
    def prescrape_chores(self):
        with JobBased() as db:
            self.num_listings = db.count("listings")
        self.start_time = datetime.now()

    def group_by_company(self, listings: list[models.Listing]) -> dict[str, list[str]]:
        """Returns listing positions grouped by company."""
        grouped_listings = {}
        for listing in listings:
            if listing.company.name not in grouped_listings:
                grouped_listings[listing.company.name] = [listing.position]
            else:
                grouped_listings[listing.company.name].append(listing.position)
        return grouped_listings

    def print_new_listings(self):
        """Print listings added to the database since the start of the last scrape."""
        with JobBased() as db:
            new_listings = db._get_listings(
                where=f"listings.date_added >= '{self.start_time}'"
            )
            num_new_listings = len(new_listings)
            self.logger.info(f"Added {num_new_listings} new listings")
        if num_new_listings > 0:
            grouped_listings = self.group_by_company(new_listings)
            print(f"Added {num_new_listings} new listings to the database:")
            for company, listings in grouped_listings.items():
                print(f"  {company}:")
                for listing in listings:
                    print(f"    {listing}")
        else:
            print("No new listings found.")
        print()

    def logprint_errors(self):
        """Print and log scrapers that had errors grouped by error type."""
        errors = helpers.get_scrapers_with_errors(self.start_time)
        for error, names in errors.items():
            if names:
                message = f"{error}:\n"
                message += "\n".join(f"  {name}" for name in names)
                if error == "no_listings":
                    self.logger.info(message)
                else:
                    self.logger.logprint(message)
                    print()

    def postscrape_chores(self):
        self.print_new_listings()
        self.logprint_errors()
        super().postscrape_chores()
        print(
            f"Total runtime: {Timer.format_time((datetime.now() - self.start_time).total_seconds())}"
        )

    def scrape(self):
        with JobBased() as db:
            listings = db.get_listings()
        execute = lambda scraper: scraper(listings).scrape()
        pool = quickpool.ThreadPool(
            [execute] * len(self.scrapers), [(scraper,) for scraper in self.scrapers]
        )
        pool.execute()


def get_inactive_scrapers() -> list[str]:
    """Return a list of scrapers marked `inactive` in the database."""
    with JobBased() as db:
        boards = db.get_inactive_boards()
    return [helpers.name_to_stem(board.company.name) for board in boards]


def main():
    finder = GruelFinder(
        ["JobScraper"],
        ["*template.py"] + [f"*{name}.py" for name in get_inactive_scrapers()],
        root / "scrapers",
    )
    scrapers = finder.find()
    jobglob = JobGlob(scrapers)
    jobglob.brew()


if __name__ == "__main__":
    main()
