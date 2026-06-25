"""Settings + JSON persistence (small, since the app does one thing).

Pure data -- no Win32.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_PORT = 4666


@dataclass
class Settings:
    listen_port: int = DEFAULT_PORT     # controller listens / follower connects here
    connect_to: str = ""                # follower: controller host/IP
    secret: str = ""                    # shared secret; set on every PC to lock down access
    # which mouse events the controller replicates
    move: bool = True
    clicks: bool = True
    wheel: bool = True
    move_rate_hz: int = 120             # cap on MOVE updates/sec (coalesced)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        valid = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in (data or {}).items() if k in valid})

    @classmethod
    def from_json(cls, text: str) -> "Settings":
        return cls.from_dict(json.loads(text))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Settings":
        p = Path(path)
        return cls.from_json(p.read_text(encoding="utf-8")) if p.exists() else cls()
