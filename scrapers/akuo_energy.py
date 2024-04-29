from typing import Any

from pathier import Pathier
from typing_extensions import override

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
import jobgruel


class JobScraper(jobgruel.SmartrecruiterGruel):
    @property
    @override
    def api_endpoint(self) -> str:
        return "https://careers.smartrecruiters.com/Akuo/en---careers-akuo/api/groups?page="
