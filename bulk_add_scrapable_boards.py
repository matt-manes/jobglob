from pathier import Pathier
from jobbased import JobBased
import helpers

root = Pathier(__file__).parent


def main():
    """ """
    boards = Pathier(__file__).with_suffix(".txt").split()
    for board in boards:
        url, company = board.split(maxsplit=1)
        url = url.strip("/")
        with JobBased() as db:
            if url not in db.scrapable_boards:
                db.add_scrapable_board(url, company)
                helpers.create_scraper_from_template(url, company)


if __name__ == "__main__":
    main()
