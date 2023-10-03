import time
from datetime import datetime

from pathier import Pathier

from jobglob import JobGlob

root = Pathier(__file__).parent


def is_business_hours() -> bool:
    now = datetime.now()
    if now.replace(hour=8) <= now <= now.replace(hour=17):
        return True
    return False


def main():
    while True:
        if is_business_hours():
            jobglob = JobGlob(["JobScraper"], ["*template.py"], root / "scrapers")
            print(f"Brewing at {datetime.now():%m/%d %I:%M %p}")
            jobglob.brew()
            print("nap time")
            del jobglob
        time.sleep(3600)


if __name__ == "__main__":
    main()
