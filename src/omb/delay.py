"""Per-PC humanization delay model (send-side).

Ported from the feature added to the original Tcl OMB. When relaying mouse/wheel
events to follower PCs, each PC is given:

* a **constant base delay** chosen once (uniform in ``[0, pc_delay_max_ms]``)
  that never changes while the PC stays connected -- so each follower behaves
  like a different person with a steady reaction lag; plus
* a **small per-event jitter** (uniform in ``[0, jitter_max_ms]``) added on top
  of every event, so no two scrolls/clicks land on a robotic fixed cadence.

Only mouse + wheel relays use this; key events stay instant, and the main PC
(where you actually click) is never delayed.

Pure logic -- the RNG is injectable so it is fully deterministic under test.
"""
from __future__ import annotations

import random


class DelayModel:
    def __init__(
        self,
        pc_delay_max_ms: int = 5000,
        jitter_max_ms: int = 150,
        rng: random.Random | None = None,
    ) -> None:
        self.pc_delay_max_ms = pc_delay_max_ms
        self.jitter_max_ms = jitter_max_ms
        self._rng = rng or random.Random()
        self._base: dict[str, int] = {}

    def base_for(self, client_id: str) -> int:
        """Return this PC's constant base delay, assigning it once on first use."""
        if client_id not in self._base:
            self._base[client_id] = self._rng.randint(0, max(0, self.pc_delay_max_ms))
        return self._base[client_id]

    def next_delay_ms(self, client_id: str) -> int:
        """Total delay (base + fresh jitter) before relaying one event to a PC."""
        jitter = self._rng.randint(0, max(0, self.jitter_max_ms))
        return self.base_for(client_id) + jitter

    def forget(self, client_id: str) -> None:
        """Drop a PC's base delay (call on disconnect)."""
        self._base.pop(client_id, None)
