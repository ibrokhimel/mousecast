"""Multi-PC networking: a main-PC server + follower client over asyncio TCP.

The **main PC** runs :class:`NetServer` (listen) and calls :meth:`NetServer.send`
to relay an input event to every connected follower. Mouse/wheel relays get the
per-PC humanization delay from :class:`~omb.delay.DelayModel`; key events go out
immediately, and the main PC's own windows are never delayed (that's the
broadcaster's job, not this module's).

A **follower** runs :class:`NetClient` (connect) and invokes a handler for each
decoded message so the local broadcaster can replay it onto that PC's windows.

Wire protocol and delay logic live in (unit-tested) ``protocol`` and ``delay``;
this module is the asyncio plumbing around them.
"""
from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from .delay import DelayModel
from .protocol import Message, ProtocolError, decode, encode, is_mouse_like

AcceptCallback = Callable[[str], bool]            # peer -> accept?
MessageHandler = Callable[[Message], None]


class NetServer:
    """Main PC: accept followers and relay events to them."""

    def __init__(
        self,
        port: int = 4464,
        *,
        delay_enabled: bool = False,
        delay_model: DelayModel | None = None,
        on_accept: AcceptCallback | None = None,
    ) -> None:
        self.port = port
        self.delay_enabled = delay_enabled
        self.delays = delay_model or DelayModel()
        self.on_accept = on_accept
        self._server: asyncio.AbstractServer | None = None
        # peer string -> writer
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
        self._clients[peer] = writer
        try:
            # followers don't talk back; just wait for disconnect
            await reader.read()
        finally:
            self._clients.pop(peer, None)
            self.delays.forget(peer)
            with contextlib.suppress(Exception):
                writer.close()

    def send(self, msg: Message) -> None:
        """Relay a message to every follower (mouse/wheel honor the per-PC delay)."""
        data = encode(msg).encode("ascii")
        delay_this = self.delay_enabled and is_mouse_like(msg)
        loop = asyncio.get_event_loop()
        for peer, writer in list(self._clients.items()):
            if delay_this:
                ms = self.delays.next_delay_ms(peer)
                loop.call_later(ms / 1000.0, self._write, peer, data)
            else:
                self._write(peer, data)

    def _write(self, peer: str, data: bytes) -> None:
        writer = self._clients.get(peer)
        if writer is None:  # disconnected while a delayed send was pending
            return
        try:
            writer.write(data)
        except Exception:  # noqa: BLE001
            self._clients.pop(peer, None)
            self.delays.forget(peer)


class NetClient:
    """Follower: connect to the main PC and dispatch incoming events."""

    def __init__(self, host: str, port: int, on_message: MessageHandler) -> None:
        self.host = host
        self.port = port
        self.on_message = on_message
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._task: asyncio.Task | None = None

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        self._task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        assert self._reader is not None
        while True:
            line = await self._reader.readline()
            if not line:
                break
            try:
                self.on_message(decode(line.decode("ascii")))
            except ProtocolError:
                continue  # ignore garbage lines, keep the link alive

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task
        if self._writer:
            self._writer.close()


def _peer(writer: asyncio.StreamWriter) -> str:
    info = writer.get_extra_info("peername")
    return f"{info[0]}:{info[1]}" if info else repr(writer)


class NetRunner:
    """Run an asyncio event loop on a background thread.

    Lets the synchronous Tkinter GUI start/stop the server, connect as a
    follower, and relay events without blocking the UI thread. All public
    methods are safe to call from the GUI thread.
    """

    def __init__(self) -> None:
        import threading

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="omb-net", daemon=True)
        self.server: NetServer | None = None
        self.client: NetClient | None = None

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def _submit(self, coro: Awaitable) -> None:
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def start_server(self, port: int, **kwargs) -> NetServer:
        self.server = NetServer(port, **kwargs)
        self._submit(self.server.start())
        return self.server

    def stop_server(self) -> None:
        if self.server:
            self._submit(self.server.stop())
            self.server = None

    def relay(self, msg: Message) -> None:
        if self.server:
            self._loop.call_soon_threadsafe(self.server.send, msg)

    def connect(self, host: str, port: int, on_message: MessageHandler) -> NetClient:
        self.client = NetClient(host, port, on_message)
        self._submit(self.client.connect())
        return self.client

    def shutdown(self) -> None:
        self.stop_server()
        if self.client:
            self._submit(self.client.close())
        self._loop.call_soon_threadsafe(self._loop.stop)
