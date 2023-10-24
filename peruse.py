import sys
import webbrowser
from dataclasses import asdict

from griddle import griddy
from pathier import Pathier

import models
from jobbased import JobBased

root = Pathier(__file__).parent

import argparse


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "key_terms",
        nargs="*",
        type=str,
        default=[],
        help=""" Only show listings with these terms in the job `position` """,
    )

    parser.add_argument(
        "-f",
        "--filter_positions",
        action="store_true",
        help=""" Use `peruse_filters.toml` to filter listings. 
        i.e. any listings with these words in the job `position` won't be shown.
        Overrides `key_terms` arg.""",
    )

    parser.add_argument(
        "-ds",
        "--default_search",
        action="store_true",
        help=""" Use the default search terms in `persuse_filters.toml` in addition to any provided `key_terms` arguments. """,
    )

    args = parser.parse_args()

    return args


def filter_listings(
    listings: list[models.Listing],
    filter_on: str,
    key_terms: list[str],
    exclude_terms: list[str],
) -> list[models.Listing]:
    filtered_listings = []

    for listing in listings:
        column = getattr(listing, filter_on).lower()
        if any(exclude in column for exclude in exclude_terms):
            continue
        if key_terms and all(key not in column for key in key_terms):
            continue
        filtered_listings.append(listing)
    return filtered_listings


def do_action(listing: models.Listing):
    while True:
        action = input(
            "Enter action ('a': add listing, 'o': open url, 'q': quit, 'i' to ignore and mark seen): "
        )
        match action:
            case "a":
                with JobBased() as db:
                    db.pin_listing(listing.id_)
                    db.mark_seen(listing.id_)
                break
            case "o":
                webbrowser.open(listing.url)
            case "q":
                sys.exit()
            case "i":
                with JobBased() as db:
                    db.mark_seen(listing.id_)
                break
            case _:
                print("oops")


def show(listing: models.Listing):
    line = asdict(listing)
    line = {
        "id": line["id_"],
        "position": line["position"],
        "company": line["company"]["name"],
        "location": line["location"],
        "url": line["url"],
    }
    print(griddy([line], "keys"))


def main(args: argparse.Namespace):
    with JobBased() as db:
        listings = db.unseen_live_listings
    filters = (root / "peruse_filters.toml").loads()
    default_search = filters["search"] if args.default_search else []
    listings = filter_listings(
        listings, "location", [], exclude_terms=filters["location"]
    )
    excludes = filters["position"] if args.filter_positions else []
    listings = filter_listings(
        listings, "position", args.key_terms + default_search, excludes
    )
    num_listings = len(listings)
    print(f"Unseen listings: {num_listings}")
    for i, listing in enumerate(listings, 1):
        print(f"{i}/{num_listings}")
        show(listing)
        do_action(listing)


if __name__ == "__main__":
    main(get_args())
