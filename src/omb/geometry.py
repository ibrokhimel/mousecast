"""Coordinate scaling between absolute screen pixels and per-window relative coords.

This is the heart of input broadcasting: a click/scroll that happens at some
point inside the *source* window must be translated to the equivalent point
inside every *target* window, even though the windows differ in size/position.

We do that by expressing the point as a fraction (xp, yp) in [0, 1] of the
source window, then multiplying back out by each target window's size.

Pure logic, no Win32 -- fully unit tested.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    """A window rectangle in absolute screen pixels."""

    x: int
    y: int
    width: int
    height: int


def abs_to_rel(x: int, y: int, rect: Rect) -> tuple[float, float]:
    """Convert an absolute screen point to (xp, yp) relative to ``rect``.

    The result is each axis as a fraction of the window size. Points inside the
    window land in [0, 1]; points outside are allowed to fall outside that range
    (the caller decides whether to clamp/ignore).
    """
    if rect.width <= 0 or rect.height <= 0:
        raise ValueError("window has non-positive size")
    xp = (x - rect.x) / rect.width
    yp = (y - rect.y) / rect.height
    return xp, yp


def rel_to_abs(xp: float, yp: float, rect: Rect) -> tuple[int, int]:
    """Convert relative (xp, yp) back to an absolute screen point in ``rect``."""
    x = round(rect.x + xp * rect.width)
    y = round(rect.y + yp * rect.height)
    return x, y


def point_in(x: int, y: int, rect: Rect) -> bool:
    """True if the absolute point lies inside ``rect``."""
    return rect.x <= x < rect.x + rect.width and rect.y <= y < rect.y + rect.height
