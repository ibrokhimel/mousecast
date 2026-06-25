"""Wire protocol for mouse replication (newline-delimited text).

The controller sends one line per mouse event; coordinates are screen fractions
in [0, 1] (see ``screen``), so they map across different resolutions.

    MOVE  <fx> <fy>
    DOWN  <fx> <fy> <button>     button = left | right | middle
    UP    <fx> <fy> <button>
    WHEEL <fx> <fy> <delta>      delta signed, in multiples of 120

Buttons are sent as separate DOWN/UP events (not "clicks") so press-drag-release
replicates faithfully. Plain text keeps it trivial to debug with nc/telnet.

Pure logic -- fully unit tested.
"""
from __future__ import annotations

from dataclasses import dataclass

BUTTONS = ("left", "right", "middle")


@dataclass(frozen=True)
class Move:
    fx: float
    fy: float


@dataclass(frozen=True)
class Button:
    fx: float
    fy: float
    button: str
    down: bool


@dataclass(frozen=True)
class Wheel:
    fx: float
    fy: float
    delta: int


Event = Move | Button | Wheel


class ProtocolError(ValueError):
    """Raised when a line cannot be parsed."""


def encode(ev: Event) -> str:
    if isinstance(ev, Move):
        return f"MOVE {_f(ev.fx)} {_f(ev.fy)}\n"
    if isinstance(ev, Button):
        cmd = "DOWN" if ev.down else "UP"
        return f"{cmd} {_f(ev.fx)} {_f(ev.fy)} {ev.button}\n"
    if isinstance(ev, Wheel):
        return f"WHEEL {_f(ev.fx)} {_f(ev.fy)} {int(ev.delta)}\n"
    raise TypeError(f"not an event: {ev!r}")


def decode(line: str) -> Event:
    parts = line.strip().split()
    if not parts:
        raise ProtocolError("empty line")
    cmd, args = parts[0], parts[1:]
    try:
        if cmd == "MOVE":
            return Move(float(args[0]), float(args[1]))
        if cmd in ("DOWN", "UP"):
            button = args[2]
            if button not in BUTTONS:
                raise ProtocolError(f"unknown button {button!r}")
            return Button(float(args[0]), float(args[1]), button, down=(cmd == "DOWN"))
        if cmd == "WHEEL":
            return Wheel(float(args[0]), float(args[1]), int(args[2]))
    except (IndexError, ValueError) as exc:
        raise ProtocolError(f"bad {cmd} line: {line!r}") from exc
    raise ProtocolError(f"unknown command {cmd!r}")


def _f(value: float) -> str:
    """Compact float that still round-trips through float()."""
    return repr(round(float(value), 6))
