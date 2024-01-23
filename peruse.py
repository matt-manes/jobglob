import argparse
import webbrowser
from dataclasses import asdict

import argshell
from griddle import griddy
from pathier import Pathier

import helpers
import models
from jobbased import JobBased

root = Pathier(__file__).parent

""" 
Go through unseen job listings and mark them as seen after choosing to ignore them or add them to your pinned listings.

Using this script means you don't have to keep looking at listings you've already seen.
"""


def get_peruse_parser() -> argshell.ArgShellParser:
    parser = argshell.ArgShellParser(
        description=""" Look through newly added job listings.
        If there is no `peruse_filters.toml` file, it will be created.
        The fields in this file can be used to filter locations and positions by text as well as set up default search terms.
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
        help=""" Use `filter_out_location_terms` in `peruse_filters.toml` to filter listings. 
        i.e. any listings with these words in the job `location` won't be shown.""",
    )

    parser.add_argument(
        "-fp",
        "--filter_positions",
        action="store_true",
        help=""" Use `filter_out_position_terms` in `peruse_filters.toml` to filter listings. 
        i.e. any listings with these words in the job `position` won't be shown.
        Overrides `key_terms` arg.""",
    )

    parser.add_argument(
        "-ds",
        "--default_search",
        action="store_true",
        help=""" Use `default_search_terms` in `persuse_filters.toml` in addition to any provided `key_terms` arguments. """,
    )

    parser.add_argument(
        "-nf",
        "--newest_first",
        action="store_true",
        help=""" Go through listings starting with the most recent.
        Default is oldest first.""",
    )

    return parser


def lower_terms(args: argshell.Namespace) -> argshell.Namespace:
    args.key_terms = [term.lower() for term in args.key_terms]
    return args


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(parents=[get_peruse_parser()], add_help=False)
    args = lower_terms(parser.parse_args())  # type: ignore
    return args


def load_filters() -> dict[str, list]:
    """Load filters from `peruse_filters.toml`.
    Create an empty file from template if it doesn't exist."""
    filter_path = root / "peruse_filters.toml"
    if not filter_path.exists():
        helpers.create_peruse_filters_from_template()
    filters = (root / "peruse_filters.toml").loads()
    return {key: [text.lower() for text in filters[key]] for key in filters}


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
    filters = load_filters()
    default_search = filters["default_search_terms"] if args.default_search else []
    if args.filter_locations:
        listings = filter_listings(
            listings, "location", [], exclude_terms=filters["filter_out_location_terms"]
        )
    excludes = filters["filter_out_position_terms"] if args.filter_positions else []
    listings = filter_listings(
        listings, "position", args.key_terms + default_search, excludes
    )
    # ========================
    peruse(listings)


if __name__ == "__main__":
    main(get_args())
