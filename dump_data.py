import re

import quickpool
from gitbetter import Git
from noiftimer import time_it
from pathier import Pathier, Pathish

from config import Config
from jobbased import JobBased

root = Pathier(__file__).parent
readme_path = root / "README.md"


def update_readme() -> bool:
    """Update the current board count in `README.md` if different.

    Returns whether the count was updated or not."""
    with JobBased() as db:
        num_boards = db.count("scrapers", where="active = 1")
        num_listings = db.count("listings", where="alive = 1")
    readme = readme_path.read_text()
    current_boards = int(re.findall(r"\*Current board count\*: ([0-9]+)", readme)[0])
    current_listings = int(re.findall(r"\*Active listings\*: ([0-9]+)", readme)[0])
    updated = False
    if num_boards != current_boards:
        print(f"Updating board count in readme from {current_boards} to {num_boards}.")
        readme = re.sub(
            r"\*Current board count\*: [0-9]+",
            f"*Current board count*: {num_boards}",
            readme,
        )
        readme_path.write_text(readme)
        updated = True
    if num_listings != current_listings:
        print(
            f"Updating listing count in readme from {current_listings} to {num_listings}."
        )
        readme = re.sub(
            r"\*Active listings\*: ([0-9]+)",
            f"*Active listings*: {num_listings}",
            readme,
        )
        readme_path.write_text(readme)
        updated = True
    return updated


@time_it()
def dump():
    """Dump data for `companies`, `boards`, and `listings` tables to `sql/jobs_data.sql`."""
    tables = ["companies", "boards", "listings"]
    config = Config.load()
    dump_path = config.sql_dir / "jobs_data.sql"

    def _dump():
        with JobBased() as db:
            db.dump_data(dump_path, tables)

    quickpool.update_and_wait(_dump)
    readme_updated = update_readme()

    git = Git()
    files: list[Pathish] = [dump_path]
    if readme_updated:
        files.append(readme_path)
    git.commit_files(files, "chore: update data")


if __name__ == "__main__":
    dump()
