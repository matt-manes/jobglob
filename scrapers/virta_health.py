from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
import jobgruel


class JobScraper(jobgruel.AshbyGruel):
    ...
