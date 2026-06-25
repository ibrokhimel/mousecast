"""Entry point: ``python -m omb`` or the ``omb`` console script.

Loads settings, then launches the Tkinter GUI. ``--headless`` is reserved for a
future follower-only daemon mode (connect + apply remote input, no UI).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Settings


def default_settings_path() -> Path:
    base = Path.home() / ".omb"
    base.mkdir(exist_ok=True)
    return base / "settings.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omb", description="Open multiboxing tool")
    parser.add_argument("--settings", type=Path, default=default_settings_path())
    parser.add_argument("--headless", action="store_true", help="follower daemon, no GUI (TODO)")
    args = parser.parse_args(argv)

    settings = Settings.load(args.settings)

    if args.headless:
        print("headless follower mode is not implemented yet", file=sys.stderr)
        return 2

    from . import gui  # imported here so --help works without a display
    gui.run(settings, args.settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
