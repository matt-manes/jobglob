from datetime import datetime

import requests
from printbuddies import PoolBar

from jobbased import JobBased


def check_listing(listing: dict) -> dict:
    response = requests.get(listing["url"])
    if response.status_code == 200 and response.url.strip("/") == listing["url"]:
        return {"url": listing["url"], "alive": True}
    return {"listing": listing, "alive": False}


def get_pool(listings: list[dict]) -> PoolBar:
    return PoolBar(
        "thread",
        [check_listing for _ in range(len(listings))],
        [(listing,) for listing in listings],
    )


def check_table(table: str):
    print(f"Checking {table}...")
    with JobBased() as db:
        listings = db.select(table, where="alive = 1", order_by="RANDOM()")
    pool = get_pool(listings)
    results = pool.execute()
    dead_count = 0
    for result in results:
        if not result["alive"]:
            dead_count += 1
            listing = result["listing"]
            with JobBased() as db:
                db.update(table, "alive", 0, f"listing_id = {listing['listing_id']}")
                db.update(
                    table,
                    "date_removed",
                    datetime.now(),
                    f"listing_id = {listing['listing_id']}",
                )
    if not dead_count:
        print("Did not find any dead listings.")
    else:
        print(f"Found {dead_count} dead listings.")


if __name__ == "__main__":
    for table in ["scraped_listings", "listings"]:
        check_table(table)
    input("...")
