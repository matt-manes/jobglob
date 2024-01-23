import functools
from dataclasses import asdict, dataclass

import dacite
from pathier import Pathier, Pathish
from typing_extensions import Optional, Self


@dataclass
class JobglobDaemon:
    glob_interval: int


@dataclass
class Config:
    logs_dir: Pathier
    scrapers_dir: Pathier
    jobglob_daemon: JobglobDaemon
    board_meta_path: Pathier
    careers_page_stubs_path: Pathier
    db_path: Pathier
    sql_dir: Pathier
    templates_dir: Pathier

    @functools.cached_property
    def scraper_logs_dir(self) -> Pathier:
        return self.logs_dir / self.scrapers_dir.stem

    @classmethod
    def load(cls, path: Pathish = Pathier(__file__).parent / "config.toml") -> Self:
        """Return a `datamodel` object populated from `path`."""
        data = Pathier(path).loads()
        for key in data:
            if key.endswith("_dir") or key.endswith("_path"):
                data[key] = Pathier(__file__).parent / data[key]
        return dacite.from_dict(cls, data)

    def dump(self, path: Pathish = Pathier(__file__).parent / "config.toml"):
        """Write the contents of this `datamodel` object to `path`."""
        data = asdict(self)
        Pathier(path).dumps(data)
