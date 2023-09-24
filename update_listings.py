import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from gitbetter import Git
from printbuddies import ProgBar
from seleniumuser import User
from jobbased import JobBased

root = Path(__file__).parent


def is_alive(url: str, xpath: str) -> bool:
    """Return True if still posted."""
    with User(headless=True) as user:
        try:
            user.get(url)
            user.find(xpath)
            return True
        except Exception as e:
            return False


def update_listings():
    with JobBased() as db:
        listings = db.live_listings
    bar = ProgBar(total=len(listings))
    with ThreadPoolExecutor() as pool:
        threads = [
            pool.submit(is_alive, listing["url"], listing["xpath"])
            for listing in listings
        ]
        while (complete := len([thread for thread in threads if thread.done()])) < len(
            threads
        ):
            bar.display(
                prefix=f"{bar.timer.elapsed_str}",
                counter_override=complete,
            )
            time.sleep(1)
        bar.display(prefix=f"{bar.timer.elapsed_str}", counter_override=len(threads))
        live_listings = [
            listing for listing, thread in zip(listings, threads) if thread.result()
        ]
        dead_listings = [
            listing for listing in listings if listing not in live_listings
        ]
    if dead_listings:
        print("The following listings appear to be dead:")
        print(*[listing["url"] for listing in dead_listings], sep="\n")
        with JobBased() as db:
            for listing in dead_listings:
                db.update("listings", "alive", 0, f"url = '{listing['url']}")
                db.update(
                    "listings",
                    "date_removed",
                    datetime.now(),
                    f"url = '{listing['url']}",
                )
    else:
        print("All previously live listings appear still live.")
    # mark live applications older than 30 days as rejected
    with JobBased() as db:
        db.mark_applications_older_than_30days_as_rejected()
    git = Git()
    git.commit_files(["jobs.db"], "chore: update listing info")
    git.push()
    input("...")


if __name__ == "__main__":
    update_listings()
