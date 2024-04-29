from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import JobviteGruel


# Url doesn't contain job board
class JobScraper(JobviteGruel): ...
