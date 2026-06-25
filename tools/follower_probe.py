#!/usr/bin/env python3
"""Connect to a controller as a fake follower and print the mouse events it sends.

Lets you verify streaming without a second real PC: run it anywhere, point it at
the controller, then move/click/scroll on the controller and watch events arrive.

    python tools/follower_probe.py <controller-host> [port]
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mousecast.net import Client  # noqa: E402

start = time.monotonic()


def on_event(ev) -> None:
    print(f"[{time.monotonic() - start:8.3f}s] {ev}")


async def main() -> None:
    # usage: follower_probe.py <host> [port] [secret]
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4666
    secret = sys.argv[3] if len(sys.argv) > 3 else ""
    client = Client(host, port, on_event, secret=secret)
    await client.connect()
    print(f"connected to {host}:{port} -- waiting for mouse events (Ctrl-C to quit)")
    try:
        await asyncio.Event().wait()
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
