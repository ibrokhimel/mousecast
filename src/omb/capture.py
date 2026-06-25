"""Find, capture and lay out game windows. WINDOWS ONLY.

Holds the mapping of *slot number* -> game-window HWND and applies the saved
per-slot layout (position/size, optional borderless). Slot 1 is the "main"
window you actually play; slots 2..N receive broadcast input.
"""
from __future__ import annotations

import re
import sys

from .config import Settings, WindowLayout
from .geometry import Rect, point_in

if sys.platform != "win32":  # pragma: no cover - guarded import
    raise ImportError("omb.capture requires Windows")

from . import winapi


class WindowManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.slots: dict[int, int] = {}  # slot -> hwnd

    def find_game_windows(self) -> list[int]:
        return winapi.find_windows(re.escape(self.settings.game))

    def capture(self, slot: int, hwnd: int) -> None:
        """Assign ``hwnd`` to ``slot`` and apply that slot's saved layout."""
        self.slots[slot] = hwnd
        if self.settings.borderless:
            winapi.make_borderless(hwnd)
        self.apply_slot(slot)

    def forget(self, slot: int) -> None:
        self.slots.pop(slot, None)

    def _layout(self, slot: int) -> WindowLayout | None:
        idx = slot - 1
        if 0 <= idx < len(self.settings.windows):
            return self.settings.windows[idx]
        return None

    def apply_slot(self, slot: int) -> None:
        layout = self._layout(slot)
        hwnd = self.slots.get(slot)
        if layout and hwnd:
            winapi.move_window(
                hwnd, Rect(layout.x, layout.y, layout.width, layout.height),
                on_top=layout.stay_on_top,
            )

    def apply_all(self) -> None:
        for slot in self.slots:
            self.apply_slot(slot)

    def rects(self) -> dict[int, Rect]:
        out: dict[int, Rect] = {}
        for slot, hwnd in self.slots.items():
            try:
                out[slot] = winapi.get_rect(hwnd)
            except Exception:  # noqa: BLE001 - window may have closed
                continue
        return out

    def slot_at(self, x: int, y: int) -> int | None:
        """Which managed slot's window contains the screen point, if any."""
        for slot, rect in self.rects().items():
            if point_in(x, y, rect):
                return slot
        return None
