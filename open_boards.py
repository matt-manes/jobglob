import time
import webbrowser

from jobbased import JobBased

if __name__ == "__main__":
    with JobBased() as db:
        urls = db.boards
    for url in urls:
        webbrowser.open(url)
        time.sleep(1)
