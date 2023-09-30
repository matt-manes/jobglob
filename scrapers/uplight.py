from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import JobviteGruel


class JobScraper(JobviteGruel):
    ...


if __name__ == "__main__":
    s = JobScraper()
    s.scrape()
