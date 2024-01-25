from pathier import Pathier

root = Pathier(__file__).parent
(root.parent).add_to_PATH()
import jobgruel


class JobScraper(jobgruel.GreenhouseGruel):
    ...


if __name__ == "__main__":
    from datetime import datetime, timedelta

    import helpers

    start = datetime.now() - timedelta(seconds=2)
    j = JobScraper()
    j.scrape()
    print(helpers.load_log(j.board.company.name).filter_dates(start))
