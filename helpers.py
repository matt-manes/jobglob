import os
from string import ascii_letters, digits

import requests
import whosyouragent
from gitbetter import Git
from pathier import Pathier

from jobbased import JobBased

root = Pathier(__file__).parent


def detect_board_type(url: str) -> str | None:
    boards = (root / "boardtype_dict.toml").loads()
    for board in boards:
        if board in url:
            return boards[board]
    return None


def extract_board_type(url: str) -> str | None:
    try:
        response = requests.get(
            url, headers={"User-Agent": whosyouragent.get_agent()}, timeout=10
        )
        return detect_board_type(response.text)
    except Exception as e:
        return None


def get_url_candidate_names(company: str) -> list[str]:
    """Returns permutations of a company name to try in a url.

    e.g. "Company Inc." returns
    "companyinc"
    "company-inc"
    "company inc"
    "CompanyInc"
    """
    alphanum = ascii_letters + digits + " -"
    candidates = [company]
    company_parts = company.split()
    candidates.extend(["".join(company_parts), "-".join(company_parts)])
    candidates.extend([candidate.lower() for candidate in candidates])
    candidates.extend(
        ["".join(ch for ch in candidate if ch in alphanum) for candidate in candidates]
    )
    return list(set(candidates))


def get_possible_urls(company: str, board_type: str) -> list[str]:
    url_formats = (root / "url_formats.toml").loads()
    names = get_url_candidate_names(company)
    template_url = url_formats[board_type]
    return [template_url.replace("$company", name) for name in names]


def try_urls(urls: list[str]) -> list[str] | None:
    valid = []
    for url in urls:
        try:
            response = requests.get(
                url, headers={"User-Agent": whosyouragent.get_agent()}, timeout=10
            )
            if response.status_code == 200 and response.url.strip("/") == url:
                valid.append(url)
        except Exception as e:
            ...
    return valid or None


def determine_board_url(company: str, url: str) -> list[str] | None:
    """Url is the company job page that's embedding a third party page."""
    board_type = extract_board_type(url)
    if not board_type:
        return None
    return try_urls(get_possible_urls(company, board_type))


def create_scraper_from_template(url: str, company: str, board_type: str | None = None):
    templates_path = root / "templates"
    if not board_type:
        board_type = detect_board_type(url)
    if not board_type:
        template = (templates_path / "template.py").read_text()
    else:
        if board_type == "greenhouse_embed":
            board_type = "greenhouse"
        template = (templates_path / f"{board_type}_template.py").read_text()
    stem = company.lower().replace(" ", "_")
    py_path = root / "scrapers" / f"{stem}.py"
    py_path.write_text(template)
    if not board_type:
        os.system(f"code -r {py_path}")


def delete_scraper(board_id: int):
    """Delete a scrapable_board record, code file, and log file given a `board_id`."""
    with JobBased() as db:
        company = db.select(
            "scrapable_boards",
            ["name", "company_id"],
            ["INNER JOIN companies ON scrapable_boards.board_id = companies.board_id"],
            where=f"scrapable_boards.board_id = {board_id}",
        )[0]
        # Don't set as `None` if the same board exists in the regular boards table.
        db.update(
            "companies",
            "board_id",
            None,
            f"name = '{company['name']}' AND {board_id} NOT IN (SELECT board_id FROM boards)",
        )
        db.update(
            "scraped_listings", "alive", 0, f"company_id = {company['company_id']}"
        )
        db.delete("scrapable_boards", f"board_id = {board_id}")
    company_stem = company["name"].lower().replace(" ", "_")
    files = list(root.rglob(f"*/{company_stem}.*"))
    git = Git()
    git.untrack(*files)
    for file in files:
        file.delete()
    # git.commit(f'-m "chore: delete `{company}` scraper"')


def main():
    """ """
    print(determine_board_url("Imply", "https://imply.io/positions"))


if __name__ == "__main__":
    main()
