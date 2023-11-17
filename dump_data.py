from gitbetter import Git
from noiftimer import time_it
from pathier import Pathier

from jobbased import JobBased

root = Pathier(__file__).parent


@time_it()
def dump():
    """Dump data for `companies`, `boards`, and `listings` tables to `sql/jobs_data.sql`."""
    tables = ["companies", "boards", "listings"]
    dump_path = root / "sql" / "jobs_data.sql"
    with JobBased() as db:
        db.dump_data(dump_path, tables)
    git = Git()
    git.commit_files([dump_path], "chore: update data")


if __name__ == "__main__":
    dump()
