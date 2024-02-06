import argparse
import webbrowser
from dataclasses import asdict

import argshell
from griddle import griddy
from pathier import Pathier
from rich import print

import models
from config import Config
from jobbased import JobBased
from peruse_filters import PeruseFilters

root = Pathier(__file__).parent
config = Config.load()
""" 
Go through unseen job listings and mark them as seen after choosing to ignore them or add them to your pinned listings.

Using this script means you don't have to keep looking at listings you've already seen.
"""


def get_peruse_parser() -> argshell.ArgShellParser:
    parser = argshell.ArgShellParser(
        description=""" Look through newly added job listings.
        If there is no `peruse_filters.toml` file, it will be created.
        The fields in this file can be used to filter locations, positions, and urls by text as well as set up default search terms.
        All fields are case insensitive.
        """
    )

    parser.add_argument(
        "key_terms",
        nargs="*",
        type=str,
        default=[],
        help=""" Only show listings with these terms in the job `position` """,
    )

    parser.add_argument(
        "-fl",
        "--filter_locations",
        action="store_true",
        help=""" Use `location_filters` in `peruse_filters.toml` to filter listings. 
        i.e. any listings with these words in the job `location` won't be shown.""",
    )

    parser.add_argument(
        "-fp",
        "--filter_positions",
        action="store_true",
        help=""" Use `position_filters` in `peruse_filters.toml` to filter listings. 
        i.e. any listings with these words in the job `position` won't be shown.
        Overrides `key_terms` arg.""",
    )

    parser.add_argument(
        "-fu",
        "--filter_urls",
        action="store_true",
        help=""" Use `url_filters` in `peruse_filters.toml` to filter listings.
    i.e. any listings with urls containing one of the terms won't be shown.""",
    )

    parser.add_argument(
        "-ds",
        "--default_search",
        action="store_true",
        help=""" Use `default_search` in `persuse_filters.toml` in addition to any provided `key_terms` arguments. """,
    )

    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help=""" Equivalent to `peruse.py -ds -fl -fp -fu -nf""",
    )

    return parser


def lower_terms(args: argshell.Namespace) -> argshell.Namespace:
    args.key_terms = [term.lower() for term in args.key_terms]
    return args


def peruse_postparser(args: argshell.Namespace) -> argshell.Namespace:
    if args.all:
        for arg in [
            "default_search",
            "filter_positions",
            "filter_locations",
            "filter_urls",
            "newest_first",
        ]:
            setattr(args, arg, True)
    args = lower_terms(args)
    return args


def get_args() -> argshell.Namespace:
    args = get_peruse_parser().parse_args()
    args = peruse_postparser(args)
    return args


def filter_listings(
    listings: list[models.Listing],
    filter_on: str,
    key_terms: list[str],
    exclude_terms: list[str],
) -> list[models.Listing]:
    """Filter `listings` on the field specified by `filter_on`."""
    filtered_listings = []
    for listing in listings:
        column = getattr(listing, filter_on).lower()
        if any(exclude in column for exclude in exclude_terms):
            continue
        if key_terms and all(key not in column for key in key_terms):
            continue
        filtered_listings.append(listing)
    return filtered_listings


def do_action(listing: models.Listing) -> bool | None:
    """Take input and perform the desired action for `listing`.

    Returns `True` if user chooses `q`: `quit`."""
    while True:
        action = input(
            "Enter action ('a': add to pinned listings, 'd': mark dead, 'o': open url, 'q': quit, 'i' to ignore and mark seen): "
        )
        match action:
            case "a":
                with JobBased() as db:
                    db.pin_listing(listing.id_)
                    db.mark_seen(listing.id_)
                break
            case "d":
                with JobBased() as db:
                    db.mark_dead(listing.id_)
                break
            case "o":
                webbrowser.open(listing.url)
            case "q":
                return True
            case "i":
                with JobBased() as db:
                    db.mark_seen(listing.id_)
                break
            case _:
                print("oops")


def show(listing: models.Listing):
    """Format and print a listing in the terminal."""
    line = asdict(listing)
    line = {
        "id": line["id_"],
        "position": line["position"],
        "company": line["company"]["name"],
        "location": line["location"],
        "date": line["date_added"],
        "url": line["url"],
    }
    print(griddy([line], "keys"))


def peruse(listings: list[models.Listing]):
    """Show each listing in `listings` and perform desired action."""
    num_listings = len(listings)
    print(f"Unseen listings: {num_listings}")
    for i, listing in enumerate(listings, 1):
        print(f"{i}/{num_listings}")
        show(listing)
        if do_action(listing):
            break


def main(args: argparse.Namespace):
    with JobBased() as db:
        listings = db.get_unseen_live_listings()
    if args.newest_first:
        listings = listings[::-1]
    # ========================
    # filter unseen listings
    # ========================
    filters = PeruseFilters.load()
    default_search = filters.default_search if args.default_search else []
    if args.filter_locations:
        listings = filter_listings(listings, "location", [], filters.location_filters)
    if args.filter_urls:
        listings = filter_listings(listings, "url", [], filters.url_filters)
    excludes = filters.position_filters if args.filter_positions else []
    listings = filter_listings(
        listings, "position", args.key_terms + default_search, excludes
    )
    # ========================
    peruse(listings)


if __name__ == "__main__":
    main(get_args())
