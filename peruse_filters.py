from dataclasses import asdict, dataclass, fields

import dacite
from rich import print
from typing_extensions import Self

import helpers
from config import Config

config = Config.load()


@dataclass
class PeruseFilters:
    position_filters: list[str]
    location_filters: list[str]
    url_filters: list[str]
    default_search: list[str]

    def __post_init__(self):
        # Set all text chunks to lowercase
        for field in fields(self):
            setattr(
                self, field.name, [chunk.lower() for chunk in getattr(self, field.name)]
            )

    @classmethod
    def load(
        cls,
    ) -> Self:
        """Return an instance of this class populated from `peruse_filters.toml`."""
        path = config.peruse_filters_path
        if not path.exists():
            print(f"{path} does not exist.")
            print("Creating from template...")
            helpers.create_peruse_filters_from_template()
        data = path.loads()
        return dacite.from_dict(cls, data)

    def dump(self):
        """Write the contents of this instance to `path`."""
        data = asdict(self)
        config.peruse_filters_path.dumps(data)
