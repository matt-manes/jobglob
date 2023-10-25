import random
from dataclasses import asdict

import quickpool
import requests

import models
from jobbased import JobBased
import logging
from pathier import Pathier

root = Pathier(__file__).parent

logger = logging.getLogger(Pathier(__file__).stem)
if not logger.hasHandlers():
    handler = logging.FileHandler(Pathier(__file__).stem + ".log")
    handler.setFormatter(
        logging.Formatter(
            "{levelname}|-|{asctime}|-|{message}",
            style="{",
            datefmt="%m/%d/%Y %I:%M:%S %p",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def is_alive(listing: models.Listing) -> bool | None:
    try:
        response = requests.get(listing.url)
        if (
            response.status_code not in [404, 410]
            and response.url.strip("/") == listing.url
        ):
            return True
        logger.info(
            f"Listing {listing.id_} at {listing.url} appears dead with code {response.status_code} and resolved url {response.url}"
        )
        return False
    except Exception as e:
        logger.exception(f"Error requesting {listing.url}")
        return None


def get_pool(listings: list[models.Listing]) -> quickpool.ThreadPool:
    return quickpool.ThreadPool(
        [is_alive for _ in range(len(listings))],
        [(listing,) for listing in listings],
    )


def check_listings() -> list[models.Listing]:
    print(f"Checking listings...")
    with JobBased() as db:
        listings = db.live_listings
    random.shuffle(listings)
    pool = get_pool(listings)
    results = pool.execute()
    dead_count = 0
    dead_listings = []
    failed_requests = []
    for result, listing in zip(results, listings):
        if result is None:
            failed_requests.append(listing)
        elif not result:
            dead_count += 1
            with JobBased() as db:
                db.mark_dead(listing.id_)
            dead_listings.append(listing)
    if not dead_count:
        print("Did not find any dead listings.")
    else:
        print(f"Found {dead_count} dead listings.")
    if failed_requests:
        print(f"{len(failed_requests)} failed requests: ")
        for request in failed_requests:
            print(f" Listing id: {request.id_} | {request.url}")

    return dead_listings


if __name__ == "__main__":
    try:
        dead_listings = check_listings()
        with JobBased() as db:
            pinned_ids = [listing.id_ for listing in db.pinned_listings]
        dead_pinned_listings = []
        for dead_listing in dead_listings:
            if dead_listing.id_ in pinned_ids:
                listing = asdict(dead_listing)
                company = listing.pop("company")
                for key in ["location", "alive", "date_added", "date_removed"]:
                    listing.pop(key)
                listing["company"] = company["name"]
                dead_pinned_listings.append(listing)
        if dead_pinned_listings:
            print("Dead pinned listings:")
            print(db.to_grid(dead_pinned_listings))
    except Exception as e:
        print(e)
    input("...")
