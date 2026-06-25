"""Resolution-independent screen coordinates.

To replicate one PC's mouse onto PCs with different screen sizes, we never send
raw pixels. The controller expresses the cursor as a *fraction* of its own
screen (0..1 on each axis); each follower multiplies that back out by its own
screen size. So "halfway across my screen" lands halfway across theirs.

Pure logic, no Win32 -- fully unit tested.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Screen:
    """Screen / virtual-desktop bounds in pixels.

    ``x``/``y`` are the top-left origin (can be negative on multi-monitor
    setups where a secondary monitor sits left of / above the primary).
    """

    x: int
    y: int
    width: int
    height: int


def to_norm(x: int, y: int, screen: Screen) -> tuple[float, float]:
    """Pixel point -> (fx, fy) fraction in [0, 1] of ``screen``."""
    if screen.width <= 0 or screen.height <= 0:
        raise ValueError("screen has non-positive size")
    fx = (x - screen.x) / screen.width
    fy = (y - screen.y) / screen.height
    return _clamp01(fx), _clamp01(fy)


def to_abs(fx: float, fy: float, screen: Screen) -> tuple[int, int]:
    """Fraction (fx, fy) -> absolute pixel point on ``screen``."""
    x = round(screen.x + _clamp01(fx) * screen.width)
    y = round(screen.y + _clamp01(fy) * screen.height)
    return x, y


def _clamp01(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v
