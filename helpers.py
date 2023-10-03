from pathier import Pathier
from jobbased import JobBased
from gitbetter import Git

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
    elif "easyapply.co" in url:
        return "easyapply"
    elif "jobs.jobvite" in url:
        return "jobvite"
    elif ".applytojob." in url:
        return "applytojob"
    else:
        return None


def create_scraper_from_template(url: str, company: str, board_type: str | None = None):
    templates_path = root / "templates"
    if not board_type:
        board_type = detect_board_type(url)
    if not board_type:
        template = (templates_path / "template.py").read_text()
    else:
        template = (templates_path / f"{board_type}_template.py").read_text()
    stem = company.lower().replace(" ", "_")
    (root / "scrapers" / f"{stem}.py").write_text(template)


def delete_scraper(board_id: int):
    """Delete a scrapable_board record, code file, and log file given a `board_id`."""
    with JobBased() as db:
        company = db.select(
            "scrapable_boards",
            ["name"],
            ["INNER JOIN companies ON scrapable_boards.board_id = companies.board_id"],
            where=f"scrapable_boards.board_id = {board_id}",
        )[0]["name"]
        # Don't set as `None` if the same board exists in the regular boards table.
        db.update(
            "companies",
            "board_id",
            None,
            f"name = '{company}' AND {board_id} NOT IN (SELECT board_id FROM boards)",
        )
        db.delete("scrapable_boards", f"board_id = {board_id}")
    company_stem = company.lower().replace(" ", "_")
    files = list(root.rglob(f"*/{company_stem}.*"))
    git = Git()
    git.untrack(*files)
    for file in files:
        file.delete()
    git.commit(f'-m "chore: delete `{company}` scraper"')
