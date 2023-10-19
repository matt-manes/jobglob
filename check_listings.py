from datetime import datetime

import requests
from griddle import griddy
from printbuddies import PoolBar

from jobbased import JobBased


def check_listing(listing: dict) -> dict:
    try:
        response = requests.get(listing["url"])
        if response.status_code == 200 and response.url.strip("/") == listing["url"]:
            return {"url": listing["url"], "alive": True}
        return {"listing": listing, "alive": False}
    except Exception as e:
        listing["error"] = str(e)
        return {"listing": listing, "alive": None}


def get_pool(listings: list[dict]) -> PoolBar:
    return PoolBar(
        "thread",
        [check_listing for _ in range(len(listings))],
        [(listing,) for listing in listings],
    )


def check_table(table: str) -> list[dict]:
    print(f"Checking {table}...")
    with JobBased() as db:
        listings = db.select(table, where="alive = 1", order_by="RANDOM()")
    pool = get_pool(listings)
    results = pool.execute()
    dead_count = 0
    dead_listings = []
    failed_requests = []
    for result in results:
        if result["alive"] is None:
            failed_requests.append(result["listing"])
        elif not result["alive"]:
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
            dead_listings.append(listing)
    if not dead_count:
        print("Did not find any dead listings.")
    else:
        print(f"Found {dead_count} dead listings.")
    if failed_requests:
        print("Failed requests:")
        for request in failed_requests:
            print(f"  {request}")
    return dead_listings


if __name__ == "__main__":
    for table in ["scraped_listings", "listings"]:
        try:
            dead_listings = check_table(table)
            if table == "listings":
                ids = (
                    "("
                    + ", ".join(str(listing["listing_id"]) for listing in dead_listings)
                    + ")"
                )
                with JobBased() as db:
                    listings = db.select(
                        "listings",
                        [
                            "listing_id AS id",
                            "position",
                            "companies.name AS company",
                            "listings.url AS url",
                        ],
                        [
                            "INNER JOIN companies ON listings.company_id = companies.company_id"
                        ],
                        where=f"listings.listing_id IN {ids}",
                    )
                print(db.to_grid(listings))
        except Exception as e:
            print(e)
    input("...")
