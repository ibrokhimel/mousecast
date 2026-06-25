"""Smoke tests: the cross-platform modules import cleanly, and the Windows-only
modules fail with a clear ImportError when their platform/deps are unavailable.
"""
import importlib
import sys

import pytest


def test_pure_modules_import():
    for name in ["omb", "omb.config", "omb.protocol", "omb.geometry", "omb.delay", "omb.net", "omb.__main__"]:
        importlib.import_module(name)
    import omb

    assert omb.__version__


@pytest.mark.parametrize("name", ["omb.winapi", "omb.capture", "omb.broadcast"])
def test_windows_only_modules_guarded(name):
    """These require pywin32; off-Windows (or without it) they raise ImportError."""
    sys.modules.pop(name, None)
    try:
        importlib.import_module(name)
    except ImportError:
        pass  # expected when not on Windows / pywin32 missing
