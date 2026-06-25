#!/usr/bin/env python3
"""Build a standalone mousecast.exe with PyInstaller (run on Windows).

    pip install -e ".[build]"
    python tools/build_exe.py

Produces dist/mousecast.exe -- a single file that needs no Python on the target
PC. Double-click it, pick Follower, enter the controller's IP + secret, Start.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The GUI lazy-imports these on Start, so make sure PyInstaller bundles them.
HIDDEN = [
    "mousecast.gui",
    "mousecast.controller",
    "mousecast.mousehook",
    "mousecast.inject",
    "mousecast.winutil",
]


def main() -> int:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--windowed", "--name", "mousecast",
        "--paths", str(ROOT / "src"),
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build"),
        "--noconfirm",
    ]
    for mod in HIDDEN:
        cmd += ["--hidden-import", mod]
    cmd.append(str(ROOT / "packaging" / "entry.py"))
    print(" ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
