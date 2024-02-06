from dataclasses import asdict, dataclass

import dacite
from typing_extensions import Self

from config import Config

config = Config.load()


@dataclass
class BoardMeta:
    boards: list[str]
    url_chunks: dict
    url_templates: dict

    @classmethod
    def load(cls) -> Self:
        """Return an instance of this class populated from `board_meta.toml`."""
        path = config.board_meta_path
        data = path.loads()
        return dacite.from_dict(cls, data)

    def dump(self):
        """Write the contents of this instance to `board_meta.toml`."""
        path = config.board_meta_path
        data = asdict(self)
        path.dumps(data)
