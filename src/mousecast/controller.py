"""Wiring: controller (capture -> send) and follower (receive -> inject).
WINDOWS ONLY (uses the hook + injector).
"""
from __future__ import annotations

import sys

from .config import Settings
from .net import NetRunner
from .protocol import Button, Event, Move, Wheel
from .screen import to_norm

if sys.platform != "win32":  # pragma: no cover - guarded import
    raise ImportError("mousecast.controller requires Windows")

from .inject import Injector
from .mousehook import MouseHook
from .winutil import virtual_screen


class Controller:
    """The one PC: capture the local mouse and stream it to all followers."""

    def __init__(self, settings: Settings, net: NetRunner) -> None:
        self.settings = settings
        self.net = net
        self.hook = MouseHook()
        self.screen = virtual_screen()
        self.running = False

    def start(self) -> None:
        self.screen = virtual_screen()
        self.hook.start()
        self.running = True

    def stop(self) -> None:
        self.hook.stop()
        self.running = False

    def pump(self) -> None:
        """Drain captured events and relay them. Call at ~move_rate_hz.

        Runs of moves are coalesced to the latest position (so we don't flood the
        network), but a pending move is always flushed *before* a click/scroll so
        the button lands at the right spot.
        """
        if not self.running:
            return
        s = self.settings
        pending: tuple[float, float] | None = None
        for kind, x, y, arg in self.hook.drain():
            fx, fy = to_norm(x, y, self.screen)
            if kind == "move":
                if s.move:
                    pending = (fx, fy)
                continue
            if pending is not None:
                self.net.send(Move(*pending))
                pending = None
            if kind in ("down", "up") and s.clicks:
                self.net.send(Button(fx, fy, arg, down=(kind == "down")))
            elif kind == "wheel" and s.wheel:
                self.net.send(Wheel(fx, fy, arg))
        if pending is not None:
            self.net.send(Move(*pending))


class Follower:
    """A receiving PC: reproduce events streamed from the controller."""

    def __init__(self) -> None:
        self.injector = Injector()

    def handle(self, ev: Event) -> None:
        try:
            self.injector.apply(ev)
        except Exception:  # noqa: BLE001 - one bad event shouldn't kill the link
            pass
