"""Multi-PC wire protocol, ported from the original OMB Tcl master/client.

The "main" PC relays input events to follower PCs over a TCP socket as simple
newline-delimited, space-separated text lines:

    MOUSE <xp> <yp> [button]    click (button "left"/"right") or move (no button)
    WHEEL <xp> <yp> <delta>     scroll wheel; delta is signed (+/- multiples of 120)
    DOWN  <keycode>             key pressed
    UP    <keycode>             key released

``xp`` / ``yp`` are floats in [0, 1] relative to the source window (see
``geometry``). Keeping the protocol as plain text (rather than a binary format)
matches the original and makes it trivial to debug with ``nc``/telnet.

Pure logic, no sockets or Win32 -- fully unit tested.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MouseMsg:
    xp: float
    yp: float
    button: str = ""  # "left", "right", or "" for a move


@dataclass(frozen=True)
class WheelMsg:
    xp: float
    yp: float
    delta: int


@dataclass(frozen=True)
class KeyMsg:
    down: bool
    keycode: int


Message = MouseMsg | WheelMsg | KeyMsg


class ProtocolError(ValueError):
    """Raised when a line cannot be parsed as a known message."""


def encode(msg: Message) -> str:
    """Serialize a message to a single protocol line (including trailing newline)."""
    if isinstance(msg, MouseMsg):
        parts = ["MOUSE", _f(msg.xp), _f(msg.yp)]
        if msg.button:
            parts.append(msg.button)
        return " ".join(parts) + "\n"
    if isinstance(msg, WheelMsg):
        return f"WHEEL {_f(msg.xp)} {_f(msg.yp)} {int(msg.delta)}\n"
    if isinstance(msg, KeyMsg):
        return f"{'DOWN' if msg.down else 'UP'} {int(msg.keycode)}\n"
    raise TypeError(f"not a protocol message: {msg!r}")


def decode(line: str) -> Message:
    """Parse a single protocol line into a message. Raises ProtocolError on junk."""
    parts = line.strip().split()
    if not parts:
        raise ProtocolError("empty line")
    cmd, args = parts[0], parts[1:]
    try:
        if cmd == "MOUSE":
            xp, yp = float(args[0]), float(args[1])
            button = args[2] if len(args) > 2 else ""
            return MouseMsg(xp, yp, button)
        if cmd == "WHEEL":
            return WheelMsg(float(args[0]), float(args[1]), int(args[2]))
        if cmd in ("DOWN", "UP"):
            return KeyMsg(down=(cmd == "DOWN"), keycode=int(args[0]))
    except (IndexError, ValueError) as exc:
        raise ProtocolError(f"bad {cmd} message: {line!r}") from exc
    raise ProtocolError(f"unknown command {cmd!r}")


def is_mouse_like(msg: Message) -> bool:
    """True for messages that get the per-PC humanization delay (mouse + wheel).

    Key events (DOWN/UP) are intentionally *not* delayed -- they stay instant.
    """
    return isinstance(msg, (MouseMsg, WheelMsg))


def _f(value: float) -> str:
    """Compact float formatting that still round-trips through ``float()``."""
    return repr(float(value))
