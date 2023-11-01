import subprocess
import sys
from pathlib import Path

root = Path(__file__).parent


def main():
    """ """
    for command in [
        ["pip", "install", "-r", "requirements.txt"],
        [sys.executable, "database_init.py"],
    ]:
        subprocess.run(command)
    (root / "gruel_logs").mkdir(exist_ok=True)


if __name__ == "__main__":
    main()
