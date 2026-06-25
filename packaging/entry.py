"""PyInstaller entry point.

Uses an absolute import so PyInstaller bundles the ``mousecast`` package
correctly -- relative imports break when a module is frozen as the top-level
script. Double-clicking the resulting exe opens the GUI; the same exe also
accepts the CLI flags (``--connect HOST`` etc.).
"""
from mousecast.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
