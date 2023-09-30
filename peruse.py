import sys
import webbrowser

from griddle import griddy
from pathier import Pathier
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

    args = parser.parse_args()

    return args


def filter_listings(
    listings: list[dict], filter_on: str, key_terms: list[str], exclude_terms: list[str]
) -> list[dict]:
    filtered_listings = []

    for listing in listings:
        column = listing[filter_on].lower()
        if any(exclude in column for exclude in exclude_terms):
            continue
        if key_terms and all(key not in column for key in key_terms):
            continue
        filtered_listings.append(listing)
    return filtered_listings


def do_action(listing: dict):
    while True:
        action = input(
            "Enter action ('a': add listing, 'o': open url, 'q': quit, 'i' to ignore and mark seen): "
        )
        match action:
            case "a":
                with JobBased() as db:
                    db.mark_intrested(listing["id"], "")
                    db.mark_seen(listing["id"])
                break
            case "o":
                webbrowser.open(listing["url"])
            case "q":
                sys.exit()
            case "i":
                with JobBased() as db:
                    db.mark_seen(listing["id"])
                break
            case _:
                print("oops")


def show(listing: dict):
    print(griddy([listing], "keys"))


def main(args: argparse.Namespace):
    with JobBased() as db:
        listings = db.unseen_listings
    filters = (root / "peruse_filters.toml").loads()
    listings = filter_listings(
        listings, "location", [], exclude_terms=filters["filters"]["location"]
    )
    if args.key_terms or args.filter_positions:
        excludes = filters["filters"]["position"] if args.filter_positions else []
        listings = filter_listings(listings, "position", args.key_terms, excludes)
    num_listings = len(listings)
    print(f"Unseen listings: {num_listings}")
    for i, listing in enumerate(listings, 1):
        print(f"{i}/{num_listings}")
        show(listing)
        do_action(listing)


if __name__ == "__main__":
    main(get_args())
