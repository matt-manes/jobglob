from pathier import Pathier
from typing import Any

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
import jobgruel


class JobScraper(jobgruel.SmartrecruiterGruel):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.api_endpoint = "https://careers.smartrecruiters.com/Akuo/en---careers-akuo/api/groups?page="
