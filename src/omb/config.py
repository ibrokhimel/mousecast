"""Settings model + JSON persistence.

Replaces the original Tcl global ``settings`` array with typed, nested
dataclasses serialized to a single JSON file. Pure data -- no Win32.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, get_type_hints

DEFAULT_HOTKEYS = {
    "capture": "ctrl+shift+c",
    "focus_next": "ctrl+shift+n",
    "focus_prev": "ctrl+shift+p",
    "swap_next": "ctrl+grave",
    "focus_main": "ctrl+shift+w",
    "reset_all": "ctrl+shift+alt+r",
    "toggle_mouse_broadcast": "ctrl+shift+m",
    "toggle_key_broadcast": "ctrl+shift+r",
}


@dataclass
class WindowLayout:
    """Saved geometry for one game-window slot, in absolute screen pixels."""

    x: int = 0
    y: int = 0
    width: int = 800
    height: int = 600
    stay_on_top: bool = False


@dataclass
class NetworkSettings:
    listen: bool = False                # this PC accepts follower connections
    listen_port: int = 4464
    connect_to: str = ""                # follower: main PC host/IP
    random_delay: bool = False          # humanize mouse/wheel relays
    pc_delay_max_ms: int = 5000         # constant per-PC base delay ceiling
    jitter_max_ms: int = 150            # per-event jitter ceiling


@dataclass
class BroadcastSettings:
    use_post_message: bool = True       # PostMessage vs synthesized input
    broadcast_delay_ms: int = 30        # settle delay around injected events
    hold_cancel_ms: int = 500           # holding a click longer cancels broadcast
    net_track_movement: bool = False    # also relay mouse moves (not just clicks)
    wheel: bool = False                 # experimental scroll-wheel broadcast
    exclude_keys: list[str] = field(default_factory=lambda: ["W", "A", "S", "D"])
    key_remap: dict[str, str] = field(default_factory=dict)


@dataclass
class Settings:
    num_windows: int = 0
    game: str = "World of Warcraft"
    auto_capture: bool = True
    borderless: bool = True
    windows: list[WindowLayout] = field(default_factory=list)
    hotkeys: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))
    network: NetworkSettings = field(default_factory=NetworkSettings)
    broadcast: BroadcastSettings = field(default_factory=BroadcastSettings)

    # ---- serialization -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        return _from_dict(cls, data)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> "Settings":
        return cls.from_dict(json.loads(text))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Settings":
        """Load settings, falling back to defaults if the file is missing."""
        p = Path(path)
        if not p.exists():
            return cls()
        return cls.from_json(p.read_text(encoding="utf-8"))


def _from_dict(klass: type, data: Any) -> Any:
    """Recursively rebuild nested dataclasses from plain dicts.

    Unknown keys are ignored and missing keys keep their dataclass defaults, so
    settings files survive version drift gracefully.
    """
    if not is_dataclass(klass):
        return data
    kwargs: dict[str, Any] = {}
    # get_type_hints resolves string annotations (from `from __future__ import
    # annotations`) back into real classes so nested dataclasses are detectable.
    type_hints = get_type_hints(klass)
    valid = set(type_hints)
    for key, value in (data or {}).items():
        if key not in valid:
            continue
        ftype = type_hints[key]
        if key == "windows" and isinstance(value, list):
            kwargs[key] = [_from_dict(WindowLayout, v) for v in value]
        elif is_dataclass(ftype) and isinstance(value, dict):
            kwargs[key] = _from_dict(ftype, value)
        else:
            kwargs[key] = value
    return klass(**kwargs)
