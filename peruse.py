import sys
import webbrowser

from griddle import griddy
from pathier import Pathier

from jobbased import JobBased

root = Pathier(__file__).parent


def filter_listings(listings: list[dict]) -> list[dict]:
    filtered_listings = []
    filters = (root / "peruse_filters.txt").split()
    for listing in listings:
        position = listing["position"].lower()
        if any(filter_ in position for filter_ in filters):
            continue
        filtered_listings.append(listing)
    return filtered_listings


def do_action(listing: dict):
    while True:
        action = input(
            "Enter action ('i': intrested, 'o': open url, 'q': quit, enter to mark seen): "
        )
        match action:
            case "i":
                xpath = f"Enter an xpath: "
                with JobBased() as db:
                    db.mark_intrested(listing["id"], xpath)
                    db.mark_seen(listing["id"])
                break
            case "o":
                webbrowser.open(listing["url"])
            case "q":
                sys.exit()
            case "":
                with JobBased() as db:
                    db.mark_seen(listing["id"])
                break
            case _:
                print("oops")


def show(listing: dict):
    print(griddy([listing], "keys"))


def main():
    with JobBased() as db:
        listings = db.unseen_listings
    listings = filter_listings(listings)
    num_listings = len(listings)
    print(f"Unseen listings: {num_listings}")
    for i, listing in enumerate(listings, 1):
        print(f"{i}/{num_listings}")
        show(listing)
        do_action(listing)


if __name__ == "__main__":
    main()
