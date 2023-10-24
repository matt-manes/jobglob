from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import SmartrecruiterGruel


class JobScraper(SmartrecruiterGruel):
    ...
