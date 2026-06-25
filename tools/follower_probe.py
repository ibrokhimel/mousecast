#!/usr/bin/env python3
"""Connect to a main OMB PC as a fake follower and print what it relays.

Lets you verify broadcasting + the per-PC humanization delay over the network
*without* a second game PC: run this on any machine, point it at the main PC,
then click/scroll on the main PC and watch the timestamped events arrive.

    python tools/follower_probe.py <main-host> [port]
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from omb.net import NetClient  # noqa: E402

start = time.monotonic()


def on_message(msg) -> None:
    t = time.monotonic() - start
    print(f"[{t:8.3f}s] {msg}")


async def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 4464
    client = NetClient(host, port, on_message)
    await client.connect()
    print(f"connected to {host}:{port} -- waiting for relayed input (Ctrl-C to quit)")
    try:
        await asyncio.Event().wait()
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
