"""Entry point: ``python -m mousecast`` / the ``mousecast`` console script.

    mousecast                      # GUI
    mousecast --listen             # controller, headless (capture + stream)
    mousecast --connect 192.168.1.5  # follower, headless (receive + reproduce)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import Settings


def default_settings_path() -> Path:
    base = Path.home() / ".mousecast"
    base.mkdir(exist_ok=True)
    return base / "settings.json"


def _run_controller(settings: Settings) -> int:
    from .controller import Controller
    from .net import NetRunner

    net = NetRunner()
    net.start()
    net.start_server(settings.listen_port)
    ctrl = Controller(settings, net)
    ctrl.start()
    period = 1.0 / max(1, settings.move_rate_hz)
    print(f"controller: listening on :{settings.listen_port}, streaming mouse (Ctrl-C to stop)")
    try:
        while True:
            ctrl.pump()
            time.sleep(period)
    except KeyboardInterrupt:
        pass
    finally:
        ctrl.stop()
        net.shutdown()
    return 0


def _run_follower(settings: Settings, host: str) -> int:
    from .controller import Follower
    from .net import NetRunner

    net = NetRunner()
    net.start()
    follower = Follower()
    net.connect(host, settings.listen_port, follower.handle)
    print(f"follower: connected to {host}:{settings.listen_port}, reproducing mouse (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        net.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mousecast", description="Replicate one PC's mouse to many PCs on the LAN")
    parser.add_argument("--settings", type=Path, default=default_settings_path())
    parser.add_argument("--listen", action="store_true", help="run as the controller (headless)")
    parser.add_argument("--connect", metavar="HOST", help="run as a follower connecting to HOST (headless)")
    parser.add_argument("--port", type=int, help="override the port")
    args = parser.parse_args(argv)

    settings = Settings.load(args.settings)
    if args.port:
        settings.listen_port = args.port

    if sys.platform != "win32" and (args.listen or args.connect):
        print("mousecast capture/inject requires Windows", file=sys.stderr)
        return 2

    if args.connect:
        return _run_follower(settings, args.connect)
    if args.listen:
        return _run_controller(settings)

    from . import gui  # imported here so --help works headless
    gui.run(settings, args.settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
