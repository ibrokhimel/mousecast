"""Shared-secret challenge/response so only PCs that know the secret can connect.

On each new connection the controller sends a random nonce; the follower replies
with ``HMAC-SHA256(secret, nonce)``. The controller recomputes and compares in
constant time. The secret itself never crosses the wire, and the per-connection
nonce stops replay.

If the configured secret is empty, the handshake still runs but effectively
accepts anyone (open mode for a fully trusted LAN). Set a secret on every PC to
lock it down.

Pure logic -- fully unit tested.
"""
from __future__ import annotations

import hmac
import secrets
from hashlib import sha256


def make_nonce() -> str:
    """A fresh random challenge (hex)."""
    return secrets.token_hex(16)


def sign(secret: str, nonce: str) -> str:
    """The follower's response: HMAC-SHA256 of the nonce keyed by the secret."""
    return hmac.new(secret.encode("utf-8"), nonce.encode("ascii"), sha256).hexdigest()


def verify(secret: str, nonce: str, response: str) -> bool:
    """Constant-time check of a follower's response."""
    return hmac.compare_digest(sign(secret, nonce), response.strip())
