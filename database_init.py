import sys

from databased import Databased
from pathier import Pathier

from config import Config

root = Pathier(__file__).parent
config = Config.load()


def init(silent_overwrite: bool = False):
    """Initialize and build database, populating with data from `sql/jobs_data.sql` if present."""
    db_path = config.db_path
    if silent_overwrite:
        db_path.delete()
    if db_path.exists():
        print(f"{db_path} already exists.")
        ans = input(
            "Type 'overwrite' to delete the current database and create a new one: "
        )
        if ans != "overwrite":
            print("Abandoning database creation.")
            sys.exit()
        else:
            print(f"Deleting {db_path}")
            db_path.delete()
    print("Building database.")
    with Databased(db_path, log_dir=config.logs_dir) as db:
        views = config.sql_dir.glob("*_view.sql")
        db.execute_script(config.sql_dir / "schema.sql")
        for view in views:
            db.execute_script(view)
        data_path = config.sql_dir / "jobs_data.sql"
        if data_path.exists():
            print("Inserting data.")
            db.execute_script(data_path)


def main():
    """ """
    print(f"Creating database `{config.db_path.stem}`...")
    init()
    input("Done, press enter to close.")


if __name__ == "__main__":
    main()
