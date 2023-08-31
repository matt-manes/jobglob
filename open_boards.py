import webbrowser
from pathlib import Path
import time

root = Path(__file__).parent

boards = (root / "jobBoards.txt").read_text().splitlines()
for board in boards:
    webbrowser.open(board)
    time.sleep(1)
