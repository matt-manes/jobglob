import subprocess
import sys


def main():
    """ """
    for command in [
        ["pip", "install", "-r", "requirements.txt"],
        [sys.executable, "database_init.py"],
    ]:
        subprocess.run(command, shell=True)


if __name__ == "__main__":
    main()
