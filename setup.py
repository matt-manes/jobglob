import subprocess
import sys
from pathlib import Path

from config import Config

root = Path(__file__).parent


def main():
    """Runs `pip install -r requirements.txt` and `database_init.py`."""
    config = Config.load()
    for command in [
        ["pip", "install", "-r", "requirements.txt"],
        [sys.executable, "database_init.py"],
    ]:
        subprocess.run(command)
    config.scraper_logs_dir.mkdir(exist_ok=True, parents=True)
    print("Some scrapers require Firefox and Geckodriver to be installed.")
    print("Firefox: https://www.mozilla.org/en-US/firefox/browsers/")
    print("Geckodriver: https://github.com/mozilla/geckodriver/releases")
    print(
        "When downloading geckodriver, either put the executable in this folder or add its location to your PATH."
    )
    input("Press enter to close...")


if __name__ == "__main__":
    main()
