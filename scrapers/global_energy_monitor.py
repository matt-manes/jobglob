from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import Bamboogruel


class JobScraper(Bamboogruel):
    ...


if __name__ == "__main__":
    g = JobScraper()
    g.scrape()
