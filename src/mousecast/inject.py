"""Reproduce mouse events on a follower PC via SendInput. WINDOWS ONLY.

Takes decoded protocol events (screen fractions) and replays them on this PC:
move the cursor to the same fractional position on the local screen, and inject
button/scroll input system-wide with SendInput.
"""
from __future__ import annotations

import sys

from .protocol import Button, Event, Move, Wheel
from .screen import to_abs

if sys.platform != "win32":  # pragma: no cover - guarded import
    raise ImportError("mousecast.inject requires Windows")

import ctypes
from ctypes import wintypes

from .winutil import user32, virtual_screen

# SendInput plumbing -------------------------------------------------------
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP = 0x0008, 0x0010
MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP = 0x0020, 0x0040
MOUSEEVENTF_WHEEL = 0x0800

_BUTTON_FLAGS = {
    ("left", True): MOUSEEVENTF_LEFTDOWN,
    ("left", False): MOUSEEVENTF_LEFTUP,
    ("right", True): MOUSEEVENTF_RIGHTDOWN,
    ("right", False): MOUSEEVENTF_RIGHTUP,
    ("middle", True): MOUSEEVENTF_MIDDLEDOWN,
    ("middle", False): MOUSEEVENTF_MIDDLEUP,
}

SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", _MOUSEINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


def _send(flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> None:
    inp = _INPUT(type=INPUT_MOUSE)
    inp.mi = _MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def _abs_move_flags(x: int, y: int) -> tuple[int, int]:
    """Convert a virtual-desktop pixel to the 0..65535 absolute range SendInput
    expects (with the VIRTUALDESK flag, the range spans all monitors)."""
    w = max(1, user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    h = max(1, user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
    vs = virtual_screen()
    nx = round((x - vs.x) * 65535 / w)
    ny = round((y - vs.y) * 65535 / h)
    return nx, ny


class Injector:
    """Apply incoming controller events to this follower's screen."""

    def __init__(self) -> None:
        self._screen = virtual_screen()

    def refresh_screen(self) -> None:
        self._screen = virtual_screen()

    def apply(self, ev: Event) -> None:
        x, y = to_abs(ev.fx, ev.fy, self._screen)
        nx, ny = _abs_move_flags(x, y)
        move = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        if isinstance(ev, Move):
            _send(move, nx, ny)
        elif isinstance(ev, Button):
            _send(move, nx, ny)  # position first, then the button event
            _send(_BUTTON_FLAGS[(ev.button, ev.down)], nx, ny)
        elif isinstance(ev, Wheel):
            _send(move, nx, ny)
            _send(MOUSEEVENTF_WHEEL, nx, ny, data=ev.delta)
