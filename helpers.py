from pathier import Pathier

root = Pathier(__file__).parent


def detect_board_type(url: str) -> str | None:
    if "boards.greenhouse.io" in url:
        return "greenhouse"
    elif "jobs.lever.co" in url:
        return "lever"
    elif "bamboohr" in url:
        return "bamboo"
    elif "jobs.ashbyhq" in url:
        return "ashby"
    elif "apply.workable" in url:
        return "workable"
    else:
        return None


def create_scraper_from_template(url: str, company: str, board_type: str | None = None):
    if not board_type:
        board_type = detect_board_type(url)
    if not board_type:
        template = (root / "scrapers" / "template.py").read_text()
    else:
        template = (root / "scrapers" / f"{board_type}_template.py").read_text()
    stem = company.lower().replace(" ", "_")
    (root / "scrapers" / f"{stem}.py").write_text(template)
