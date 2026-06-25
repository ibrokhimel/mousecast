#!/usr/bin/env python3
"""Launch N copies of a game/app, staggered -- a cross-platform replacement for
the original launchwow*.bat helpers.

    python tools/launch_game.py "C:/Path/To/Game.exe" --count 3 --stagger 2
    python tools/launch_game.py "C:/Path/To/Game.exe" -n 2 -- --windowed -arg

Everything after a literal ``--`` is passed through to the game unchanged.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Launch N staggered game windows")
    parser.add_argument("exe", help="path to the game/app executable")
    parser.add_argument("-n", "--count", type=int, default=2, help="how many to launch")
    parser.add_argument("-s", "--stagger", type=float, default=2.0, help="seconds between launches")
    parser.add_argument("passthrough", nargs="*", help="args after -- go to the game")
    args = parser.parse_args(argv)

    extra = args.passthrough
    if extra and extra[0] == "--":
        extra = extra[1:]

    for i in range(1, args.count + 1):
        print(f"launching {i}/{args.count}: {args.exe} {' '.join(extra)}")
        subprocess.Popen([args.exe, *extra])
        if i < args.count:
            time.sleep(args.stagger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
