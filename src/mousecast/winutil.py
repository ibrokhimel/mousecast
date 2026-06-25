"""Tiny shared Win32 helpers (screen bounds). WINDOWS ONLY.

Kept separate so both the capture (controller) and inject (follower) sides can
ask "how big is this PC's screen?" without importing each other.
"""
from __future__ import annotations

import sys

from .screen import Screen

if sys.platform != "win32":  # pragma: no cover - guarded import
    raise ImportError("mousecast.winutil requires Windows")

import ctypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

# GetSystemMetrics indices for the full virtual desktop (all monitors combined)
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


def virtual_screen() -> Screen:
    """Bounds of the whole virtual desktop (spanning every monitor)."""
    gsm = user32.GetSystemMetrics
    return Screen(
        x=gsm(SM_XVIRTUALSCREEN),
        y=gsm(SM_YVIRTUALSCREEN),
        width=gsm(SM_CXVIRTUALSCREEN),
        height=gsm(SM_CYVIRTUALSCREEN),
    )
