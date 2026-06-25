# mousecast

Replicate **one PC's mouse onto many PCs** on your local network, in real time.

One **controller** PC captures its mouse — movement, clicks and scroll — and
streams it to any number of **follower** PCs on the LAN, which reproduce it on
their own screens simultaneously. Works with any Windows app (it operates on the
whole screen, not on specific windows). That's the whole tool.

> **Status: early scaffold.** The cross‑platform *core* (wire protocol,
> resolution‑independent coordinates, settings) is implemented and **unit‑tested**
> (runs in CI). The **Windows layer** — the global mouse hook that captures input
> and the `SendInput` injector that reproduces it — is written but needs
> validation on real Windows PCs with `pywin32`; it can't run in CI.

## How it works

- The controller installs a low‑level mouse hook (`WH_MOUSE_LL`) and captures
  every move / button / wheel event.
- Each event's position is sent as a **fraction of the screen** (0–1 on each
  axis), so it maps correctly onto follower PCs even at different resolutions.
- Followers reproduce each event with `SendInput`: move the cursor to the same
  fractional spot, then replay the button/scroll.
- Movement is coalesced to a capped rate so it doesn't flood the network; clicks
  and scrolls are sent immediately and in order.

```
src/mousecast/
  screen.py     # resolution-independent (0..1) coordinates   (pure, tested)
  protocol.py   # mouse-event wire protocol                    (pure, tested)
  config.py     # settings + JSON                              (pure, tested)
  net.py        # asyncio controller(server)/follower(client)  + background runner
  winutil.py    # virtual-desktop bounds                       (Windows-only)
  mousehook.py  # WH_MOUSE_LL capture of move/click/wheel       (Windows-only)
  inject.py     # reproduce events via SendInput                (Windows-only)
  controller.py # capture->send (controller) / receive->inject (follower)
  gui.py        # tiny Tkinter front end
tools/
  follower_probe.py   # connect as a fake follower, print received events
```

## Install & run

```bash
# pure core only (any OS) — enough to run the tests
pip install -e ".[dev]"
pytest -q

# full app, on Windows
pip install -e ".[win,dev]"
```

Run it (Windows). **Controller** (the PC whose mouse you want to share):

```bash
mousecast --listen            # headless,   or just `mousecast` for the GUI
```

**Each follower** PC:

```bash
mousecast --connect 192.168.1.50    # the controller's LAN IP
```

Open the chosen TCP port (default **4666**) inbound in Windows Firewall on the
controller. Tip: `python tools/follower_probe.py <controller-ip>` shows the
event stream from any machine, so you can test without a second Windows PC.

## Caveats

- It moves the **real cursor** on each follower — those PCs follow along, they
  aren't independent while connected.
- Different aspect ratios stretch the mapping (fractional, per axis); identical
  resolutions are exact.
- Security: this injects input on every follower. Run it only on a **trusted
  LAN** — there's no authentication yet.

## License

GPLv3 (see [`LICENSE`](LICENSE)). Originally derived from the design of
[OpenMultiBoxing](https://github.com/OpenMultiBoxing/OpenMultiBoxing) (MooreaTV
et al.), then reduced to this single purpose.
