from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
import models
from jobgruel import JobGruel


class JobScraper(JobGruel):
    @property
    def api_url(self) -> str:
        return f"{self.board.url}/JobBoardView/LoadSearchResults"

    @property
    def api_payload(self) -> dict:
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

    def get_parsable_items(self) -> list[dict]:
        response = self.request(
            self.api_url,
            "post",
            headers={
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip, deflate",
            },
            json_=self.api_payload,
        )
        return response.json()["opportunities"]

    def parse_item(self, item: dict) -> models.Listing | None:
        try:
            listing = self.new_listing()
            listing.position = item["Title"]
            if item["Locations"]:
                listing.location = item["Locations"][0]["LocalizedDescription"]
            else:
                listing.location = "Unlisted"
            listing.url = (
                f"{self.board.url}/OpportunityDetail?opportunityId={item['Id']}"
            )
            return listing
        except Exception as e:
            self.logger.exception("Failure to parse item:")
            self.logger.error(str(item))
            self.fail_count += 1
            return None
