from pathier import Pathier

import helpers
from jobbased import JobBased

root = Pathier(__file__).parent


def main():
    """ """
    with JobBased() as db:
        existing_board_urls = [board.url for board in db.boards]
    boards = Pathier(__file__).with_suffix(".txt").split()
    for board in boards:
        url, company = board.split(maxsplit=1)
        url = url.strip("/")
        if url not in existing_board_urls:
            with JobBased() as db:
                db.add_board(url, company)
                helpers.create_scraper_from_template(url, company)


if __name__ == "__main__":
    main()
