from typing import Any

import gruel
from pathier import Pathier
from typing_extensions import override

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
import models
from jobgruel import JobGruel


class JobScraper(JobGruel):
    @property
    def api_url(self) -> str:
        return f"{self.board.url}/JobBoardView/LoadSearchResults"

    @property
    def api_payload(self) -> dict[str, Any]:
        return {
            "opportunitySearch": {
                "Top": 1000,
                "Skip": 0,
                "QueryString": "",
                "OrderBy": [
                    {
                        "Value": "postedDateDesc",
                        "PropertyName": "PostedDate",
                        "Ascending": False,
                    }
                ],
                "Filters": [
                    {
                        "t": "TermsSearchFilterDto",
                        "fieldName": 4,
                        "extra": None,
                        "values": [],
                    },
                    {
                        "t": "TermsSearchFilterDto",
                        "fieldName": 5,
                        "extra": None,
                        "values": [],
                    },
                    {
                        "t": "TermsSearchFilterDto",
                        "fieldName": 6,
                        "extra": None,
                        "values": [],
                    },
                ],
            },
            "matchCriteria": {
                "PreferredJobs": [],
                "Educations": [],
                "LicenseAndCertifications": [],
                "Skills": [],
                "hasNoLicenses": False,
                "SkippedSkills": [],
            },
        }

    @override
    def get_source(self) -> gruel.Response:
        headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        return self.request(
            self.api_url, "post", headers=headers, json=self.api_payload
        )

    @override
    def get_parsable_items(self, source: gruel.Response) -> list[dict[str, Any]]:
        return source.json()["opportunities"]

    @override
    def parse_item(self, item: dict[str, Any]) -> models.Listing | None:
        listing = self.new_listing()
        listing.position = item["Title"]
        if item["Locations"]:
            listing.location = item["Locations"][0]["LocalizedDescription"]
        else:
            listing.location = "Unlisted"
        listing.url = f"{self.board.url}/OpportunityDetail?opportunityId={item['Id']}"
        return listing
