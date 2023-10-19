from bs4 import Tag
from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
from jobgruel import GreenhouseGruel


class JobScraper(GreenhouseGruel):
    def parse_item(self, item: Tag) -> dict | None:
        data = super().parse_item(item)
        if data:
            url = data["url"]
            data["url"] = url[: url.rfind("?gh")]
        return data
