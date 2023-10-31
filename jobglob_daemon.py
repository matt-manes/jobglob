import time
from datetime import datetime, timedelta

import loggi
from noiftimer import Timer
from pathier import Pathier
from printbuddies import print_in_place

from jobglob import JobGlob

root = Pathier(__file__).parent


class JobGlobDaemon:
    def __init__(self):
        self._last_glob_time = None

    @property
    def business_hours(self) -> tuple[int, int]:
        # Assuming local time is CST: start 8 am EST and end 5 pm PST
        # (7 am - 7 pm CST)
        return (7, 19)

    @property
    def is_weekend(self) -> bool:
        return datetime.now().weekday in [5, 6]

    @property
    def glob_interval(self) -> int:
        """Number of seconds between globbings."""
        return 3600

    @property
    def logpath(self) -> Pathier:
        return root / "jobglob.log"

    @property
    def seconds_since_last_glob(self) -> float:
        return (datetime.now() - self.last_glob_time).total_seconds()

    @property
    def last_glob_time(self) -> datetime:
        if not self._last_glob_time:
            if self.logpath.exists():
                logs = loggi.load_log(self.logpath).filter_messages(["Brew complete"])
                if logs.num_events:
                    self._last_glob_time = logs.events[-1].date
            else:
                self._last_glob_time = datetime.fromtimestamp(0)
        assert self._last_glob_time
        return self._last_glob_time

    @last_glob_time.setter
    def last_glob_time(self, time: datetime):
        self._last_glob_time = time

    @property
    def seconds_until_next_glob(self) -> float:
        if self.is_weekend:
            return self.seconds_until_monday_business_start
        if not self.is_business_hours:
            return self.seconds_until_business_hours
        return self.glob_interval - self.seconds_since_last_glob

    @property
    def is_business_hours(self) -> bool:
        now = datetime.now()
        if (
            now.replace(hour=self.business_hours[0], minute=0, second=0, microsecond=0)
            <= now
            <= now.replace(
                hour=self.business_hours[1], minute=0, second=0, microsecond=0
            )
        ):
            return True
        return False

    @property
    def seconds_until_monday_business_start(self) -> float:
        now = datetime.now()
        monday = (now + timedelta(days=7 - now.weekday())).replace(
            hour=self.business_hours[0], minute=0, second=0, microsecond=0
        )
        return (monday - now).total_seconds()

    @property
    def seconds_until_business_hours(self) -> float:
        now = datetime.now()
        start, stop = self.business_hours
        business_start = now.replace(hour=start, minute=0, second=0, microsecond=0)
        business_stop = now.replace(hour=stop, minute=0, second=0, microsecond=0)
        if now < business_start:
            return (business_start - now).total_seconds()
        if business_stop < now:
            return ((business_start + timedelta(days=1)) - now).total_seconds()
        return 0

    def nap(self):
        while (seconds := self.seconds_until_next_glob) > 0:
            print_in_place(f"Sleeping for {Timer.format_time(seconds)}", True)
            time.sleep(60)

    def run(self):
        while True:
            self.nap()
            jobglob = JobGlob(["JobScraper"], ["*template.py"], root / "scrapers")
            print(f"Brewing at {datetime.now():%m/%d %I:%M %p}")
            jobglob.brew()
            self.last_glob_time = datetime.now()
            del jobglob


def main():
    daemon = JobGlobDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
