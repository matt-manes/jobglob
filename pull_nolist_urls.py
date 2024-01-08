import loggi
from pathier import Pathier

from jobbased import JobBased

root = Pathier(__file__).parent


def main():
    """ """
    event = (
        loggi.load_log(root / "jobglob.log")
        .filter_messages(["*no_listings*"])
        .events[-1]
    )
    stems = [stem.strip() for stem in event.message.split()[1:]]
    urls = []
    with JobBased() as db:
        for stem in stems:
            urls.append(db.get_board(stem).url)
    print(*urls, sep="\n")


if __name__ == "__main__":
    main()
