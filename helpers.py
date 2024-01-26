import os
from datetime import datetime
from typing import Generator

import loggi
import loggi.models
from pathier import Pathier

import board_detector
from config import Config

root = Pathier(__file__).parent
config = Config.load()


def name_to_stem(name: str) -> str:
    """Convert to lowercase and replace spaces with underscores."""
    return name.lower().replace(" ", "_")


def stem_to_name(stem: str) -> str:
    """Replace underscores with spaces and capitalize first letters."""
    return " ".join(word.capitalize() for word in stem.split("_"))


def create_scraper_from_template(url: str, company: str, board_type: str | None = None):
    """Create scraper file from template and write to scrapers directory given a `url` and `company`."""
    templates_path = config.templates_dir
    detector = board_detector.BoardDetector()
    if not board_type:
        board_type = detector.get_board_type_from_text(url)
    if not board_type:
        template = (templates_path / "template.py").read_text()
    else:
        if board_type == "greenhouse_embed":
            board_type = "greenhouse"
        template = (
            (templates_path / "subgruel_template.py")
            .read_text()
            .replace("JobGruel", f"{board_type.capitalize()}Gruel")
        )
    stem = name_to_stem(company)
    py_path = config.scrapers_dir / f"{stem}.py"
    if py_path.exists():
        raise FileExistsError(f"The file '{py_path}' already exists.")
    py_path.write_text(template)
    if not board_type:
        os.system(f"code -r {py_path}")


def create_peruse_filters_from_template():
    """Create a blank `peruse_filters.toml` file from the template."""
    template_path = config.templates_dir / "peruse_filters_template.toml"
    template_path.copy(root / "peruse_filters.toml")
