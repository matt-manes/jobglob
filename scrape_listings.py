import subprocess
from jobbased import JobBased
import requests
from whosyouragent import whosyouragent

if __name__ == "__main__":
    subprocess.run(["brew_gruel", "JobScraper", "-e", "*template.py", "-p", "scrapers"])
