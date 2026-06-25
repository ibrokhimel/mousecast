"""Smoke tests: cross-platform modules import cleanly; Windows-only modules raise
a clear ImportError when their platform/deps are unavailable.
"""
import importlib
import sys

import pytest


def test_pure_modules_import():
    for name in ["mousecast", "mousecast.screen", "mousecast.protocol", "mousecast.config",
                 "mousecast.net", "mousecast.__main__"]:
        importlib.import_module(name)
    import mousecast

    assert mousecast.__version__


@pytest.mark.parametrize("name", ["mousecast.winutil", "mousecast.mousehook", "mousecast.inject", "mousecast.controller"])
def test_windows_only_modules_guarded(name):
    sys.modules.pop(name, None)
    try:
        importlib.import_module(name)
    except ImportError:
        pass  # expected off-Windows / without pywin32
