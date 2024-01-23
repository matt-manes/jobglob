import random
from dataclasses import asdict

import loggi
import quickpool
import requests
from griddle import griddy
from pathier import Pathier

import models
from config import Config
from jobbased import JobBased

root = Pathier(__file__).parent
config = Config.load()
logger = loggi.getLogger(Pathier(__file__).stem, config.logs_dir)


def is_alive(listing: models.Listing) -> bool | None:
    """Returns whether `listing` is alive or not.

    If dead, mark it as such in the database.

    A listing is considered alive if it doesn't return a 404 or 410 status code and does not redirect.
    """
    try:
        response = requests.get(listing.url)
    except Exception as e:
        logger.exception(f"Error requesting {listing.url}")
        return None
    if (
        response.status_code not in [404, 410]
        and response.url.strip("/") == listing.url
    ):
        return True
    with JobBased() as db:
        db.mark_dead(listing.id_)
    logger.info(
        f"Listing {listing.id_} at {listing.url} appears dead with code {response.status_code} and resolved url {response.url}"
    )
    return False


def get_pool(listings: list[models.Listing]) -> quickpool.ThreadPool:
    """Return a `quickpool.ThreadPool` object primed to run `is_alive()` on `listings`."""
    return quickpool.ThreadPool(
        [is_alive for _ in range(len(listings))],
        [(listing,) for listing in listings],
    )


def get_live_listings() -> list[models.Listing]:
    """Returns a list of currently alive listings."""
    with JobBased() as db:
        listings = db.get_live_listings()
    random.shuffle(listings)
    return listings


def find_dead_listings(listings: list[models.Listing]) -> list[models.Listing]:
    """Check for and return dead listings."""
    pool = get_pool(listings)
    results = pool.execute()
    return [listing for listing, result in zip(listings, results) if result == False]


def get_dead_pinned_listings(
    dead_listings: list[models.Listing],
) -> list[models.Listing]:
    """Given a list of dead listings, return a list of those that were pinned."""
    with JobBased() as db:
        pinned_ids = [listing.id_ for listing in db.get_pinned_listings()]
    return [listing for listing in dead_listings if listing.id_ in pinned_ids]


def listings_to_grid(listings: list[models.Listing]) -> str:
    """Convert a list of listings to a printable grid."""
    converted_listings = []
    for listing in listings:
        listing = asdict(listing)
        for key in ["location", "alive", "date_added", "date_removed"]:
            listing.pop(key)
        listing["company"] = listing.pop("company")["name"]
        converted_listings.append(listing)
    return griddy(converted_listings, "keys")


def check_listings():
    """Check if any live listings are dead."""
    try:
        listings = get_live_listings()
        print(f"Scanning {len(listings)} listings...")
        dead_listings = find_dead_listings(listings)
        if not dead_listings:
            print("Did not find any dead listings.")
        else:
            print(f"Found {len(dead_listings)} dead listings.")
            dead_pinned_listings = get_dead_pinned_listings(dead_listings)
            if dead_pinned_listings:
                print("Dead pinned listings:")
                print(listings_to_grid(dead_pinned_listings))
    except Exception as e:
        print(e)
    with JobBased() as db:
        db.mark_applications_older_than_30days_as_rejected()
    input("Press enter to close...")


if __name__ == "__main__":
    check_listings()
