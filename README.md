# omb-py

Open multiboxing tool for Windows — broadcast your keyboard, mouse clicks and
scroll wheel to many game windows at once, and across several PCs. A clean‑room
**Python rewrite** of [OpenMultiBoxing](https://github.com/OpenMultiBoxing/OpenMultiBoxing)
(originally a single 4000‑line Tcl/Tk script), restructured into a small, typed,
testable package.

> **Status: early scaffold.** The cross‑platform *core* (wire protocol,
> coordinate scaling, per‑PC delay, settings) is implemented and **unit‑tested**
> (`pytest`, runs in CI). The **Windows layer** (window capture, input
> injection, the low‑level scroll‑wheel hook, and the Tkinter GUI) is written
> but needs validation on a real Windows box with `pywin32` — it can't be
> exercised in CI. See [What works / what's next](#what-works--whats-next).

## Why a rewrite

The original is powerful but is one big Tcl file. This port keeps the proven
*ideas* (PostMessage input injection, per‑window coordinate scaling, the
master/follower multi‑PC protocol, the per‑PC "humanization" delay, the
`WH_MOUSE_LL` scroll hook) but separates the **pure logic** (easy to read and
test) from the **Win32 plumbing**.

## Architecture

```
src/omb/
  config.py     # typed settings + JSON persistence          (pure, tested)
  protocol.py   # multi-PC wire protocol encode/decode        (pure, tested)
  geometry.py   # abs <-> per-window relative coordinates     (pure, tested)
  delay.py      # per-PC humanization delay model             (pure, tested)
  net.py        # asyncio master/follower sockets             (uses protocol+delay)
  winapi.py     # Win32 wrappers: windows, input, keys        (Windows-only)
  wheelhook.py  # WH_MOUSE_LL scroll-wheel capture (ctypes)   (Windows-only)
  capture.py    # find / capture / lay out game windows       (Windows-only)
  broadcast.py  # ties capture + injection + net together     (Windows-only)
  gui.py        # Tkinter front end                           (lazy Win32)
tools/
  follower_probe.py  # connect as a fake follower, print relayed events
  launch_game.py     # launch N staggered game windows (replaces the .bat files)
tests/          # pytest suite for the pure core
```

The Win32 modules raise `ImportError` off‑Windows on purpose, so the pure core
stays importable and testable everywhere.

## Install & run

```bash
# pure core only (any OS) — enough to run the tests
pip install -e ".[dev]"
pytest -q

# full app, on Windows
pip install -e ".[win,dev]"
python -m omb            # or:  omb
```

## Features

- **Window layout & capture** — find your game windows by title, tile them,
  optional borderless.
- **Mouse broadcasting** — replay a click on the focused window to every other
  window (PostMessage), with per‑window coordinate scaling.
- **Scroll‑wheel broadcasting (experimental)** — a `WH_MOUSE_LL` hook captures
  the wheel (which can't be polled) and relays it like clicks.
- **Multi‑PC** — one main PC relays input to follower PCs over TCP (default port
  `4464`).
- **Per‑PC humanization delay** — each follower gets a constant random base
  delay (0–5 s, configurable) assigned once, plus small per‑event jitter, so the
  followers don't act in robotic lockstep. Applies to mouse + wheel only; keys
  and the main PC stay instant.

### Multi‑PC setup

1. **Main PC:** tick **Listen for followers** (default port 4464). Open that
   port inbound in Windows Firewall.
2. **Each follower:** enter the main PC's IP in **Connect to main PC** → Connect.
3. Capture each PC's own game windows, then broadcast on the main PC.

Tip: run `python tools/follower_probe.py <main-ip>` from any machine to watch the
relayed events (and the delay) without needing a second game PC.

## What works / what's next

| Area | State |
|------|-------|
| protocol / geometry / delay / config | ✅ implemented + unit‑tested |
| asyncio multi‑PC server/client + NetRunner | ✅ implemented (integration‑level) |
| Win32 window capture / layout / injection | ✍️ written — **validate on Windows** |
| `WH_MOUSE_LL` scroll‑wheel hook (ctypes) | ✍️ written — **validate on Windows** |
| Tkinter GUI wiring | ✍️ written — **validate on Windows** |
| Key broadcasting (down/up + remap/exclude) | ⏳ next — structure in place |
| Global hotkeys, focus‑follow‑mouse, overlay | ⏳ not ported yet |

## License & attribution

GPLv3 (see [`LICENSE`](LICENSE)). This is a derivative of **OpenMultiBoxing** by
MooreaTV and contributors — <https://github.com/OpenMultiBoxing/OpenMultiBoxing>.
Use responsibly and within each game's rules.
