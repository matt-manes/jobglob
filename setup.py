import subprocess
import sys
from pathlib import Path

root = Path(__file__).parent


def main():
    """Runs `pip install -r requirements.txt` and `database_init.py`."""
    for command in [
        ["pip", "install", "-r", "requirements.txt"],
        [sys.executable, "database_init.py"],
    ]:
        subprocess.run(command)
    (root / "gruel_logs").mkdir(exist_ok=True)
    print("Some scrapers require Firefox and Geckodriver to be installed.")
    print("Firefox:")
    print("https://www.mozilla.org/en-US/firefox/browsers/")
    print("Geckodriver:")
    print("https://github.com/mozilla/geckodriver/releases")
    print(
        "When downloading geckodriver, either put the executable in this folder or add its location to your PATH."
    )


if __name__ == "__main__":
    main()
