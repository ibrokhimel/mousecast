"""Tkinter front end.

Importable anywhere (the Windows-only bits are lazy-imported when you actually
start broadcasting), so the GUI module itself can be smoke-tested off-Windows.
The UI binds directly to a :class:`~omb.config.Settings` instance.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from .config import Settings

POLL_MS = 50  # broadcaster tick interval (matches the original mouseWatchInterval)


class App(ttk.Frame):
    def __init__(self, master: tk.Tk, settings: Settings, settings_path: Path) -> None:
        super().__init__(master, padding=10)
        self.master = master
        self.settings = settings
        self.settings_path = settings_path
        self.grid(sticky="nsew")

        # runtime objects (created on Start, Windows-only)
        self._windows = None
        self._broadcaster = None
        self._net = None
        self._wheelhook = None

        # tk vars bound to settings
        s, n, b = settings, settings.network, settings.broadcast
        self.v_num = tk.IntVar(value=s.num_windows)
        self.v_listen = tk.BooleanVar(value=n.listen)
        self.v_port = tk.IntVar(value=n.listen_port)
        self.v_connect = tk.StringVar(value=n.connect_to)
        self.v_random = tk.BooleanVar(value=n.random_delay)
        self.v_pcmax = tk.IntVar(value=n.pc_delay_max_ms)
        self.v_jitter = tk.IntVar(value=n.jitter_max_ms)
        self.v_mouse = tk.BooleanVar(value=False)
        self.v_wheel = tk.BooleanVar(value=b.wheel)
        self.v_status = tk.StringVar(value="idle")

        self._build()

    # -- layout ----------------------------------------------------------
    def _build(self) -> None:
        self.master.title("omb-py -- Open MultiBoxing")
        r = 0

        ttk.Label(self, text="Windows:").grid(row=r, column=0, sticky="w")
        ttk.Spinbox(self, from_=0, to=32, width=5, textvariable=self.v_num).grid(row=r, column=1, sticky="w")
        ttk.Button(self, text="Capture game windows", command=self.on_capture).grid(row=r, column=2, sticky="ew")
        r += 1

        ttk.Separator(self).grid(row=r, column=0, columnspan=3, sticky="ew", pady=6); r += 1
        ttk.Label(self, text="Broadcast", font="-weight bold").grid(row=r, column=0, sticky="w"); r += 1
        ttk.Checkbutton(self, text="Mouse clicks", variable=self.v_mouse, command=self.on_toggle).grid(row=r, column=0, columnspan=2, sticky="w"); r += 1
        ttk.Checkbutton(self, text="Scroll wheel (experimental)", variable=self.v_wheel, command=self.on_toggle).grid(row=r, column=0, columnspan=2, sticky="w"); r += 1

        ttk.Separator(self).grid(row=r, column=0, columnspan=3, sticky="ew", pady=6); r += 1
        ttk.Label(self, text="Multi-PC", font="-weight bold").grid(row=r, column=0, sticky="w"); r += 1
        ttk.Checkbutton(self, text="Listen for followers", variable=self.v_listen, command=self.on_listen).grid(row=r, column=0, columnspan=2, sticky="w")
        ttk.Label(self, text="port").grid(row=r, column=2, sticky="e")
        ttk.Entry(self, width=6, textvariable=self.v_port).grid(row=r, column=2, sticky="w"); r += 1
        ttk.Label(self, text="Connect to main PC:").grid(row=r, column=0, sticky="w")
        ttk.Entry(self, width=16, textvariable=self.v_connect).grid(row=r, column=1, sticky="w")
        ttk.Button(self, text="Connect", command=self.on_connect).grid(row=r, column=2, sticky="ew"); r += 1

        ttk.Checkbutton(self, text="Random per-PC delay (humanize)", variable=self.v_random).grid(row=r, column=0, columnspan=2, sticky="w"); r += 1
        ttk.Label(self, text="base max (ms)").grid(row=r, column=0, sticky="e")
        ttk.Entry(self, width=8, textvariable=self.v_pcmax).grid(row=r, column=1, sticky="w")
        ttk.Label(self, text="jitter max (ms)").grid(row=r, column=2, sticky="w"); r += 1
        ttk.Entry(self, width=8, textvariable=self.v_jitter).grid(row=r, column=1, sticky="w"); r += 1

        ttk.Separator(self).grid(row=r, column=0, columnspan=3, sticky="ew", pady=6); r += 1
        ttk.Button(self, text="Save settings", command=self.on_save).grid(row=r, column=0, sticky="ew")
        ttk.Label(self, textvariable=self.v_status, foreground="#0a0").grid(row=r, column=1, columnspan=2, sticky="w"); r += 1

    # -- settings sync ---------------------------------------------------
    def _pull(self) -> None:
        s, n, b = self.settings, self.settings.network, self.settings.broadcast
        s.num_windows = self.v_num.get()
        n.listen, n.listen_port, n.connect_to = self.v_listen.get(), self.v_port.get(), self.v_connect.get()
        n.random_delay, n.pc_delay_max_ms, n.jitter_max_ms = self.v_random.get(), self.v_pcmax.get(), self.v_jitter.get()
        b.wheel = self.v_wheel.get()

    def on_save(self) -> None:
        self._pull()
        self.settings.save(self.settings_path)
        self.v_status.set(f"saved {self.settings_path.name}")

    # -- actions (Windows-only paths lazy-imported) ----------------------
    def _ensure_runtime(self):
        from . import winapi  # noqa: F401  (ensures we're on Windows)
        from .broadcast import MouseBroadcaster
        from .capture import WindowManager
        from .net import NetRunner
        from .wheelhook import WheelHook

        if self._windows is None:
            self._pull()
            self._windows = WindowManager(self.settings)
            self._net = NetRunner(); self._net.start()
            self._wheelhook = WheelHook()
            self._broadcaster = MouseBroadcaster(self.settings, self._windows, net=None, wheelhook=self._wheelhook)
            self.after(POLL_MS, self._tick)
        return self._broadcaster

    def on_capture(self) -> None:
        try:
            b = self._ensure_runtime()
        except ImportError:
            self.v_status.set("capture needs Windows + pywin32")
            return
        hwnds = self._windows.find_game_windows()
        for i, hwnd in enumerate(hwnds[: self.v_num.get()], start=1):
            self._windows.capture(i, hwnd)
        self.v_status.set(f"captured {len(self._windows.slots)} window(s)")

    def on_toggle(self) -> None:
        try:
            b = self._ensure_runtime()
        except ImportError:
            self.v_status.set("broadcast needs Windows + pywin32")
            return
        self._pull()
        on = self.v_mouse.get() or self.v_wheel.get()
        b.set_enabled(on)
        self.v_status.set("broadcasting" if on else "stopped")

    def on_listen(self) -> None:
        try:
            self._ensure_runtime()
        except ImportError:
            self.v_status.set("networking needs Windows for injection")
            return
        self._pull()
        from .delay import DelayModel
        if self.v_listen.get():
            self._net.start_server(
                self.v_port.get(),
                delay_enabled=self.settings.network.random_delay,
                delay_model=DelayModel(self.v_pcmax.get(), self.v_jitter.get()),
            )
            # broadcaster relays to followers through the runner
            self._broadcaster.net = _RunnerNet(self._net)
            self.v_status.set(f"listening on {self.v_port.get()}")
        else:
            self._net.stop_server()
            self._broadcaster.net = None
            self.v_status.set("stopped listening")

    def on_connect(self) -> None:
        try:
            self._ensure_runtime()
        except ImportError:
            self.v_status.set("follower needs Windows for injection")
            return
        self._pull()
        from .broadcast import apply_remote
        self._net.connect(self.v_connect.get(), self.v_port.get(),
                           lambda msg: apply_remote(msg, self.settings, self._windows))
        self.v_status.set(f"connected to {self.v_connect.get()}")

    def _tick(self) -> None:
        if self._broadcaster:
            try:
                self._broadcaster.tick()
            except Exception as exc:  # noqa: BLE001 - keep the UI alive
                self.v_status.set(f"tick error: {exc}")
        self.after(POLL_MS, self._tick)


class _RunnerNet:
    """Adapts NetRunner to the small ``.send(msg)`` interface the broadcaster wants."""

    def __init__(self, runner) -> None:
        self._runner = runner

    def send(self, msg) -> None:
        self._runner.relay(msg)


def run(settings: Settings, settings_path: Path) -> None:
    root = tk.Tk()
    App(root, settings, settings_path)
    root.mainloop()
