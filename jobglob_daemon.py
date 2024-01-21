import time
from datetime import datetime, timedelta

import loggi
from noiftimer import Timer
from pathier import Pathier
from printbuddies import print_in_place

import jobglob

root = Pathier(__file__).parent


class JobGlobDaemon:
    """Daemonize running `jobglob.py`.

    Runs once an hour Monday -> Friday between 7 am and 7 pm.

    Use `jobglob.py` to run ad hoc.
    """

    def __init__(self):
        self._last_glob_time = None

    @property
    def business_hours(self) -> tuple[int, int]:
        """Returns `(7, 19)`."""
        # Assuming local time is CST: start 8 am EST and end 5 pm PST
        # (7 am - 7 pm CST)
        return (7, 19)

    @property
    def glob_interval(self) -> int:
        """Number of seconds between globbings."""
        return 3600

    @property
    def is_business_hours(self) -> bool:
        """Returns if the current time is during business hours (according to `self.business_hours`)."""
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
    def is_weekend(self) -> bool:
        """Returns if the current time is a weekday."""
        return datetime.now().weekday() in [5, 6]

    @property
    def last_glob_time(self) -> datetime:
        """Returns the last time a scrape was run, whether by this file of `jobglob.py`."""
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
    def logpath(self) -> Pathier:
        """Log path for `jobglob.log`."""
        return root / "jobglob.log"

    @property
    def seconds_since_last_glob(self) -> float:
        """The number of seconds since the last time `jobglob.JobGlob().brew()` was run."""
        return (datetime.now() - self.last_glob_time).total_seconds()

    @property
    def seconds_until_business_hours(self) -> float:
        """The number of seconds between now and the next business hours window (according to `self.business_hours`)."""
        now = datetime.now()
        start, stop = self.business_hours
        business_start = now.replace(hour=start, minute=0, second=0, microsecond=0)
        business_stop = now.replace(hour=stop, minute=0, second=0, microsecond=0)
        if now < business_start:
            return (business_start - now).total_seconds()
        if business_stop < now:
            return (business_start + timedelta(days=1) - now).total_seconds()
        return 0

    @property
    def seconds_until_monday_business_start(self) -> float:
        """The number of seconds between now and business hours on the upcoming Monday (according to `self.business_hours`)."""
        now = datetime.now()
        monday = (now + timedelta(days=7 - now.weekday())).replace(
            hour=self.business_hours[0], minute=0, second=0, microsecond=0
        )
        return (monday - now).total_seconds()

    @property
    def seconds_until_next_glob(self) -> float:
        """The number of seconds until the next `jobglob.JobGlob().brew()` should be run."""
        if self.is_weekend:
            return self.seconds_until_monday_business_start
        if not self.is_business_hours:
            return self.seconds_until_business_hours
        return self.glob_interval - self.seconds_since_last_glob

    def nap(self):
        """Sleep until next glob.

        Update the terminal display with how long is left in one minute intervals."""
        while (seconds := self.seconds_until_next_glob) > 0:
            print_in_place(f"Sleeping for {Timer.format_time(seconds)}", True)
            time.sleep(60)

    def run(self):
        """Call to run indefinitely."""
        while True:
            self.nap()
            print(f"Brewing at {datetime.now():%m/%d %I:%M %p}")
            jobglob.main()
            self.last_glob_time = datetime.now()


def main():
    daemon = JobGlobDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
