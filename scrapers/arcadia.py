from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import Levergruel


class JobScraper(Levergruel):
    ...


if __name__ == "__main__":
    gruel = JobScraper()
    gruel.scrape()
