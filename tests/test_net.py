"""Integration tests for the auth handshake over a real local socket (no Win32)."""
import asyncio

from mousecast.net import Client, Server
from mousecast.protocol import Move


def _port(server: Server) -> int:
    assert server._server is not None
    return server._server.sockets[0].getsockname()[1]


def test_correct_secret_receives_events():
    async def scenario():
        received = []
        server = Server(0, secret="k")
        await server.start()
        client = Client("127.0.0.1", _port(server), received.append, secret="k")
        await client.connect()
        await asyncio.sleep(0.1)  # let the handshake finish + register
        assert server.clients  # follower accepted
        server.send(Move(0.5, 0.25))
        await asyncio.sleep(0.1)
        await client.close()
        await server.stop()
        return received

    received = asyncio.run(scenario())
    assert received == [Move(0.5, 0.25)]


def test_wrong_secret_rejected():
    async def scenario():
        received = []
        server = Server(0, secret="correct")
        await server.start()
        client = Client("127.0.0.1", _port(server), received.append, secret="WRONG")
        await client.connect()
        await asyncio.sleep(0.1)
        n_clients = len(server.clients)
        server.send(Move(0.5, 0.5))  # should reach nobody
        await asyncio.sleep(0.1)
        await client.close()
        await server.stop()
        return n_clients, received

    n_clients, received = asyncio.run(scenario())
    assert n_clients == 0
    assert received == []
