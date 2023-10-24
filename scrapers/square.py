from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import SmartrecruiterGruel


class JobScraper(SmartrecruiterGruel):
    ...


def main():
    """ """
    s = JobScraper()
    s.scrape()


if __name__ == "__main__":
    main()
