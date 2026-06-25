"""Input broadcaster: capture input on the window under the cursor, replay to all
the others (and to follower PCs). WINDOWS ONLY.

Mirrors the original OMB flow:

* **Clicks/moves** are detected by polling (``GetAsyncKeyState`` + cursor pos)
  on a periodic ``tick()`` -- the same model the Tcl version uses.
* **Scroll** comes from the :class:`~omb.wheelhook.WheelHook` queue (the wheel
  has no pollable state), drained each tick.

For every captured event we figure out which managed window the cursor is over,
express the point as a fraction of that window (``geometry``), then replay it to
the *other* local windows via ``winapi`` and to follower PCs via ``NetServer``.
The window under the cursor already got the real event, so it is skipped.
"""
from __future__ import annotations

import sys

from .config import Settings
from .geometry import abs_to_rel, rel_to_abs
from .protocol import MouseMsg, WheelMsg

if sys.platform != "win32":  # pragma: no cover - guarded import
    raise ImportError("omb.broadcast requires Windows")

from . import winapi
from .capture import WindowManager

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02


class MouseBroadcaster:
    def __init__(self, settings: Settings, windows: WindowManager, net=None, wheelhook=None) -> None:
        self.settings = settings
        self.windows = windows
        self.net = net               # optional NetServer (main PC)
        self.wheelhook = wheelhook   # optional WheelHook
        self.enabled = False
        self._lbtn_was_down = False
        self._rbtn_was_down = False

    # -- lifecycle -------------------------------------------------------
    def set_enabled(self, on: bool) -> None:
        self.enabled = on
        if self.wheelhook and self.settings.broadcast.wheel:
            self.wheelhook.start() if on else self.wheelhook.stop()

    # -- per-frame poll --------------------------------------------------
    def tick(self) -> None:
        if not self.enabled:
            return
        self._poll_clicks()
        if self.settings.broadcast.wheel and self.wheelhook:
            self._drain_wheel()

    def _poll_clicks(self) -> None:
        l_down = winapi.async_key_down(VK_LBUTTON)
        r_down = winapi.async_key_down(VK_RBUTTON)
        # fire on the release edge, like the original (press-then-release = a click)
        if self._lbtn_was_down and not l_down:
            self._broadcast_click("left")
        if self._rbtn_was_down and not r_down:
            self._broadcast_click("right")
        self._lbtn_was_down, self._rbtn_was_down = l_down, r_down

    def _broadcast_click(self, button: str) -> None:
        x, y = winapi.cursor_pos()
        src = self.windows.slot_at(x, y)
        if src is None:
            return
        rects = self.windows.rects()
        xp, yp = abs_to_rel(x, y, rects[src])
        self._relay(MouseMsg(xp, yp, button), src, rects, lambda hwnd, sx, sy: self._post_click(hwnd, sx, sy, button))

    def _drain_wheel(self) -> None:
        for x, y, delta in self.wheelhook.drain():
            src = self.windows.slot_at(x, y)
            if src is None:
                continue
            rects = self.windows.rects()
            xp, yp = abs_to_rel(x, y, rects[src])
            self._relay(WheelMsg(xp, yp, delta), src, rects, lambda hwnd, sx, sy: winapi.post_wheel(hwnd, sx, sy, delta))

    def _relay(self, msg, src_slot, rects, inject) -> None:
        # to follower PCs (NetServer applies the per-PC humanization delay)
        if self.net is not None:
            self.net.send(msg)
        # to the other local windows
        for slot, rect in rects.items():
            if slot == src_slot:
                continue
            sx, sy = rel_to_abs(msg.xp, msg.yp, rect)
            hwnd = self.windows.slots.get(slot)
            if hwnd:
                inject(hwnd, sx, sy)

    def _post_click(self, hwnd: int, screen_x: int, screen_y: int, button: str) -> None:
        if self.settings.broadcast.use_post_message:
            cx, cy = winapi.screen_to_client(hwnd, screen_x, screen_y)
            winapi.post_click(hwnd, cx, cy, button)
        else:
            winapi.set_cursor_pos(screen_x, screen_y)
            # (synthesized-input path would go here; PostMessage is the default)


def apply_remote(msg, settings: Settings, windows: WindowManager) -> None:
    """Apply a message received from the main PC onto this follower's windows.

    Used by the NetClient handler on a follower PC.
    """
    rects = windows.rects()
    for slot, rect in rects.items():
        hwnd = windows.slots.get(slot)
        if not hwnd:
            continue
        sx, sy = rel_to_abs(msg.xp, msg.yp, rect) if hasattr(msg, "xp") else (0, 0)
        if isinstance(msg, MouseMsg) and msg.button:
            cx, cy = winapi.screen_to_client(hwnd, sx, sy)
            winapi.post_click(hwnd, cx, cy, msg.button)
        elif isinstance(msg, WheelMsg):
            winapi.post_wheel(hwnd, sx, sy, msg.delta)
