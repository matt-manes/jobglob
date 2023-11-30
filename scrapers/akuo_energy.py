from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
import jobgruel


class JobScraper(jobgruel.SmartrecruiterGruel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_endpoint = "https://careers.smartrecruiters.com/Akuo/en---careers-akuo/api/groups?page="


if __name__ == "__main__":
    import helpers
    from datetime import datetime, timedelta

    start = datetime.now() - timedelta(seconds=2)
    j = JobScraper()
    j.scrape()
    print(helpers.load_log(j.board.company.name).filter_dates(start))
