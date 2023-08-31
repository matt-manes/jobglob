import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from databased import DataBased
from printbuddies import ProgBar
from seleniumuser import User

root = Path(__file__).parent

with DataBased("joblistings.db") as db:
    db.create_table(
        "listings",
        [
            "name text",
            "company text",
            "url text unique",
            "applied int",
            "rejected int",
            "alive int",
            "xpath text",
            "date_added timestamp",
            "date_applied timestamp",
            "date_removed timestamp",
            "date_rejected timestamp",
        ],
    )


def is_alive(url: str, xpath: str) -> bool:
    """Return True if still posted."""
    with User(headless=False) as user:
        try:
            user.get(url)
            user.find(xpath)
            return True
        except Exception as e:
            return False


def update_listings():
    with DataBased("joblistings.db") as db:
        listings = db.get_rows("listings", [("alive", 1)])
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
        with DataBased("joblistings.db") as db:
            for listing in dead_listings:
                db.update("listings", "alive", 0, [("url", listing["url"])])
                db.update(
                    "listings",
                    "date_removed",
                    datetime.now(),
                    [("url", listing["url"])],
                )
            for row in db.get_rows("listings", {"applied": 1, "rejected": 0}):
                if (datetime.now() - row["date_applied"]).days > 30:
                    db.update("listings", "rejected", 1, [("url", row["url"])])
                    db.update(
                        "listings",
                        "date_rejected",
                        datetime.now(),
                        [("url", row["url"])],
                    )
    else:
        print("All previously live listings appear still live.")
    input("...")


if __name__ == "__main__":
    update_listings()
