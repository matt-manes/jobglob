from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import AshbyGruel


class JobScraper(AshbyGruel):
    ...
