import loggi
from pathier import Pathier

from config import Config
from jobbased import JobBased

root = Pathier(__file__).parent
config = Config.load()


def main():
    """Print scrapers that didn't find any listings on their last run."""
    event = (
        loggi.load_log(config.logs_dir / "jobglob.log")
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
