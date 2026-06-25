"""Thin Win32 wrappers: window management + input injection + key state.

WINDOWS ONLY (imports pywin32). All raw Win32 lives here so the rest of the app
speaks plain Python. This module is *not* covered by the cross-platform test
suite -- validate behavior on a real Windows box.

Install the dependency with:  pip install ".[win]"
"""
from __future__ import annotations

import sys

from .geometry import Rect

if sys.platform != "win32":  # pragma: no cover - guarded import
    raise ImportError("omb.winapi requires Windows (pywin32)")

import re

import win32api
import win32con
import win32gui

# --- window messages used for input injection ---------------------------
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MOUSEWHEEL = 0x020A
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101

_BUTTON_MSGS = {
    "left": (WM_LBUTTONDOWN, WM_LBUTTONUP, 0x0001),   # MK_LBUTTON
    "right": (WM_RBUTTONDOWN, WM_RBUTTONUP, 0x0002),  # MK_RBUTTON
}


# --- window discovery / geometry ----------------------------------------
def find_windows(title_regex: str) -> list[int]:
    """Return HWNDs of top-level visible windows whose title matches a regex."""
    rx = re.compile(title_regex, re.IGNORECASE)
    found: list[int] = []

    def _cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if text and rx.search(text):
                found.append(hwnd)

    win32gui.EnumWindows(_cb, None)
    return found


def get_rect(hwnd: int) -> Rect:
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return Rect(left, top, right - left, bottom - top)


def move_window(hwnd: int, rect: Rect, *, on_top: bool = False) -> None:
    after = win32con.HWND_TOPMOST if on_top else win32con.HWND_NOTOPMOST
    win32gui.SetWindowPos(
        hwnd, after, rect.x, rect.y, rect.width, rect.height, win32con.SWP_SHOWWINDOW
    )


def make_borderless(hwnd: int) -> None:
    """Strip caption/thick-frame so the game window tiles cleanly."""
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME)
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
    win32gui.SetWindowPos(
        hwnd, 0, 0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED,
    )


def set_foreground(hwnd: int) -> None:
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:  # noqa: BLE001 - foreground can fail per OS focus rules
        pass


# --- cursor / hit testing -----------------------------------------------
def cursor_pos() -> tuple[int, int]:
    return win32api.GetCursorPos()


def set_cursor_pos(x: int, y: int) -> None:
    win32api.SetCursorPos((x, y))


def window_at(x: int, y: int) -> int:
    return win32gui.WindowFromPoint((x, y))


def async_key_down(vk: int) -> bool:
    """True if the virtual key is currently down (high bit of GetAsyncKeyState)."""
    return (win32api.GetAsyncKeyState(vk) & 0x8000) != 0


# --- input injection (PostMessage) --------------------------------------
def post_click(hwnd: int, client_x: int, client_y: int, button: str) -> None:
    """Post a click to ``hwnd`` at *client* coordinates."""
    down, up, mk = _BUTTON_MSGS[button]
    lparam = (client_y << 16) | (client_x & 0xFFFF)
    win32gui.PostMessage(hwnd, WM_MOUSEMOVE, 0, lparam)
    win32gui.PostMessage(hwnd, down, mk, lparam)
    win32gui.PostMessage(hwnd, up, 0, lparam)


def post_wheel(hwnd: int, screen_x: int, screen_y: int, delta: int) -> None:
    """Post a scroll to ``hwnd``. WM_MOUSEWHEEL uses *screen* coords in lParam."""
    wparam = (delta & 0xFFFF) << 16
    lparam = ((screen_y & 0xFFFF) << 16) | (screen_x & 0xFFFF)
    win32gui.PostMessage(hwnd, WM_MOUSEWHEEL, wparam, lparam)


def post_key(hwnd: int, vk: int, *, down: bool) -> None:
    win32gui.PostMessage(hwnd, WM_KEYDOWN if down else WM_KEYUP, vk, 0)


def screen_to_client(hwnd: int, x: int, y: int) -> tuple[int, int]:
    return win32gui.ScreenToClient(hwnd, (x, y))
