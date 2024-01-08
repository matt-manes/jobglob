import sys

from databased import Databased
from pathier import Pathier

root = Pathier(__file__).parent


def init(db_name: str, silent_overwrite: bool = False):
    db_path = root / db_name
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
    with Databased(db_path) as db:
        views = (root / "sql").glob("*_view.sql")
        db.execute_script(root / "sql" / "schema.sql")
        for view in views:
            db.execute_script(view)
        data_path = root / "sql" / "jobs_data.sql"
        if data_path.exists():
            print("Inserting data.")
            db.execute_script(data_path)


def main():
    """ """
    print(f"Creating database...")
    init("jobs.db")
    input("Done, press enter to close.")


if __name__ == "__main__":
    main()
