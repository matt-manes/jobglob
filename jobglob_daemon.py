import time
from datetime import datetime

from pathier import Pathier

from jobglob import JobGlob
from noiftimer import Timer

root = Pathier(__file__).parent


def is_business_hours() -> bool:
    now = datetime.now()
    if now.replace(hour=8) <= now <= now.replace(hour=17):
        return True
    return False


def get_last_brew_time() -> datetime:
    logpath = root / "brewer.log"
    if logpath.exists():
        logs = (root / "brewer.log").split()[::-1]
        for log in logs:
            if "Brew complete." in log:
                date = log.split("|-|")[1]
                return datetime.strptime(date, "%m/%d/%Y %I:%M:%S %p")
    return datetime.fromtimestamp(0)


def check_last_brew_time():
    last_brew_time = get_last_brew_time()
    seconds_since_last_brew = (datetime.now() - last_brew_time).total_seconds()
    if seconds_since_last_brew < 3600:
        sleep_time = 3600 - seconds_since_last_brew
        print(f"Sleeping for {Timer.format_time(sleep_time)}")
        time.sleep(sleep_time)


def main():
    while True:
        if is_business_hours():
            check_last_brew_time()
            jobglob = JobGlob(["JobScraper"], ["*template.py"], root / "scrapers")
            print(f"Brewing at {datetime.now():%m/%d %I:%M %p}")
            jobglob.brew()
            print("nap time")
            del jobglob
        time.sleep(3600)


if __name__ == "__main__":
    main()
