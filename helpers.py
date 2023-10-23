import os

from pathier import Pathier

import board_detector

root = Pathier(__file__).parent


def create_scraper_from_template(url: str, company: str, board_type: str | None = None):
    templates_path = root / "templates"
    if not board_type:
        board_type = board_detector.get_board_type_from_text(url)
    if not board_type:
        template = (templates_path / "template.py").read_text()
    else:
        if board_type == "greenhouse_embed":
            board_type = "greenhouse"
        template = (
            (templates_path / "subgruel_template.py)")
            .read_text()
            .replace("JobGruel", f"{board_type.capitalize()}Gruel")
        )
    stem = company.lower().replace(" ", "_")
    py_path = root / "scrapers" / f"{stem}.py"
    py_path.write_text(template)
    if not board_type:
        os.system(f"code -r {py_path}")
