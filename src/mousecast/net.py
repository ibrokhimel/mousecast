"""LAN networking: a controller (server) streams mouse events to followers.

The **controller** runs :class:`Server` (listen) and calls :meth:`Server.send`
to push each mouse event to every connected follower, immediately (real-time;
no artificial delay). A **follower** runs :class:`Client` (connect) and invokes
a handler for each decoded event so it can be reproduced locally.

Wire format lives in (unit-tested) ``protocol``; this is the asyncio plumbing.
"""
from __future__ import annotations

import asyncio
import contextlib
import threading
from collections.abc import Awaitable, Callable

from . import auth
from .protocol import Event, ProtocolError, decode, encode

AcceptCallback = Callable[[str], bool]
EventHandler = Callable[[Event], None]

HANDSHAKE_TIMEOUT = 5.0


class AuthError(Exception):
    """Raised when the shared-secret handshake fails."""


class Server:
    """Controller side: accept followers and broadcast events to them."""

    def __init__(self, port: int, *, secret: str = "", on_accept: AcceptCallback | None = None) -> None:
        self.port = port
        self.secret = secret
        self.on_accept = on_accept
        self._server: asyncio.AbstractServer | None = None
        self._clients: dict[str, asyncio.StreamWriter] = {}

    @property
    def clients(self) -> list[str]:
        return list(self._clients)

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, host="0.0.0.0", port=self.port)

    async def stop(self) -> None:
        for w in list(self._clients.values()):
            w.close()
        self._clients.clear()
        if self._server:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()
            self._server = None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = _peer(writer)
        if self.on_accept and not self.on_accept(peer):
            writer.close()
            return
        try:
            await self._authenticate(reader, writer)
        except (AuthError, asyncio.TimeoutError, ConnectionError):
            with contextlib.suppress(Exception):
                writer.close()
            return
        self._clients[peer] = writer
        try:
            await reader.read()  # followers don't talk back; wait for disconnect
        finally:
            self._clients.pop(peer, None)
            with contextlib.suppress(Exception):
                writer.close()

    async def _authenticate(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Send a nonce challenge; require a correct HMAC reply before streaming."""
        nonce = auth.make_nonce()
        writer.write(f"HELLO {nonce}\n".encode("ascii"))
        await writer.drain()
        line = await asyncio.wait_for(reader.readline(), HANDSHAKE_TIMEOUT)
        parts = line.decode("ascii", "replace").split()
        if len(parts) != 2 or parts[0] != "AUTH" or not auth.verify(self.secret, nonce, parts[1]):
            raise AuthError("bad secret")

    def send(self, ev: Event) -> None:
        data = encode(ev).encode("ascii")
        for peer, writer in list(self._clients.items()):
            try:
                writer.write(data)
            except Exception:  # noqa: BLE001
                self._clients.pop(peer, None)


class Client:
    """Follower side: connect to the controller and dispatch incoming events."""

    def __init__(self, host: str, port: int, on_event: EventHandler, *, secret: str = "") -> None:
        self.host = host
        self.port = port
        self.on_event = on_event
        self.secret = secret
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._task: asyncio.Task | None = None

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        await self._authenticate()
        self._task = asyncio.create_task(self._read_loop())

    async def _authenticate(self) -> None:
        """Answer the controller's nonce challenge with our HMAC."""
        assert self._reader is not None and self._writer is not None
        line = await asyncio.wait_for(self._reader.readline(), HANDSHAKE_TIMEOUT)
        parts = line.decode("ascii", "replace").split()
        if len(parts) != 2 or parts[0] != "HELLO":
            raise AuthError("no challenge from controller")
        self._writer.write(f"AUTH {auth.sign(self.secret, parts[1])}\n".encode("ascii"))
        await self._writer.drain()

    async def _read_loop(self) -> None:
        assert self._reader is not None
        while True:
            line = await self._reader.readline()
            if not line:
                break
            try:
                self.on_event(decode(line.decode("ascii")))
            except ProtocolError:
                continue  # ignore junk, keep the link alive

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
            # CancelledError is a BaseException, so suppress(Exception) misses it
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
        if self._writer:
            self._writer.close()


class NetRunner:
    """Run an asyncio loop on a background thread so a sync GUI can drive it.

    All methods are safe to call from the GUI/main thread.
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="mousecast-net", daemon=True)
        self.server: Server | None = None
        self.client: Client | None = None

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def _submit(self, coro: Awaitable) -> None:
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def start_server(self, port: int, **kwargs) -> Server:
        self.server = Server(port, **kwargs)
        self._submit(self.server.start())
        return self.server

    def stop_server(self) -> None:
        if self.server:
            self._submit(self.server.stop())
            self.server = None

    def send(self, ev: Event) -> None:
        if self.server:
            self._loop.call_soon_threadsafe(self.server.send, ev)

    def connect(self, host: str, port: int, on_event: EventHandler, *, secret: str = "") -> Client:
        self.client = Client(host, port, on_event, secret=secret)
        self._submit(self.client.connect())
        return self.client

    def shutdown(self) -> None:
        self.stop_server()
        if self.client:
            self._submit(self.client.close())
        self._loop.call_soon_threadsafe(self._loop.stop)


def _peer(writer: asyncio.StreamWriter) -> str:
    info = writer.get_extra_info("peername")
    return f"{info[0]}:{info[1]}" if info else repr(writer)
