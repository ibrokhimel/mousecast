"""Tiny Tkinter front end. Importable anywhere; Win32 bits are lazy-imported on
Start so the module can be smoke-tested off-Windows.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .config import Settings


class App(ttk.Frame):
    def __init__(self, master: tk.Tk, settings: Settings, settings_path: Path) -> None:
        super().__init__(master, padding=12)
        self.master = master
        self.settings = settings
        self.settings_path = settings_path
        self.grid(sticky="nsew")

        self._net = None
        self._controller = None
        self._follower = None
        self._pumping = False

        self.v_role = tk.StringVar(value="controller")
        self.v_port = tk.IntVar(value=settings.listen_port)
        self.v_host = tk.StringVar(value=settings.connect_to)
        self.v_move = tk.BooleanVar(value=settings.move)
        self.v_clicks = tk.BooleanVar(value=settings.clicks)
        self.v_wheel = tk.BooleanVar(value=settings.wheel)
        self.v_status = tk.StringVar(value="idle")
        self._build()

    def _build(self) -> None:
        self.master.title("mousecast")
        r = 0
        ttk.Label(self, text="This PC is the…", font="-weight bold").grid(row=r, column=0, columnspan=3, sticky="w"); r += 1
        ttk.Radiobutton(self, text="Controller (send my mouse)", value="controller", variable=self.v_role).grid(row=r, column=0, columnspan=3, sticky="w"); r += 1
        ttk.Radiobutton(self, text="Follower (reproduce a mouse)", value="follower", variable=self.v_role).grid(row=r, column=0, columnspan=3, sticky="w"); r += 1

        ttk.Separator(self).grid(row=r, column=0, columnspan=3, sticky="ew", pady=6); r += 1
        ttk.Label(self, text="Port").grid(row=r, column=0, sticky="e")
        ttk.Entry(self, width=8, textvariable=self.v_port).grid(row=r, column=1, sticky="w"); r += 1
        ttk.Label(self, text="Controller IP\n(followers only)", justify="right").grid(row=r, column=0, sticky="e")
        ttk.Entry(self, width=16, textvariable=self.v_host).grid(row=r, column=1, sticky="w"); r += 1

        ttk.Separator(self).grid(row=r, column=0, columnspan=3, sticky="ew", pady=6); r += 1
        ttk.Label(self, text="Replicate", font="-weight bold").grid(row=r, column=0, sticky="w"); r += 1
        ttk.Checkbutton(self, text="Movement", variable=self.v_move).grid(row=r, column=0, sticky="w")
        ttk.Checkbutton(self, text="Clicks", variable=self.v_clicks).grid(row=r, column=1, sticky="w")
        ttk.Checkbutton(self, text="Wheel", variable=self.v_wheel).grid(row=r, column=2, sticky="w"); r += 1

        ttk.Separator(self).grid(row=r, column=0, columnspan=3, sticky="ew", pady=6); r += 1
        self.btn = ttk.Button(self, text="Start", command=self.on_start)
        self.btn.grid(row=r, column=0, sticky="ew")
        ttk.Button(self, text="Save", command=self.on_save).grid(row=r, column=1, sticky="ew")
        ttk.Label(self, textvariable=self.v_status, foreground="#0a0").grid(row=r, column=2, sticky="w"); r += 1

    def _pull(self) -> None:
        s = self.settings
        s.listen_port, s.connect_to = self.v_port.get(), self.v_host.get()
        s.move, s.clicks, s.wheel = self.v_move.get(), self.v_clicks.get(), self.v_wheel.get()

    def on_save(self) -> None:
        self._pull()
        self.settings.save(self.settings_path)
        self.v_status.set(f"saved {self.settings_path.name}")

    def on_start(self) -> None:
        if self._net is not None:
            self._stop()
            return
        self._pull()
        try:
            from .net import NetRunner
        except Exception as exc:  # noqa: BLE001
            self.v_status.set(str(exc)); return
        self._net = NetRunner(); self._net.start()
        try:
            if self.v_role.get() == "controller":
                from .controller import Controller
                self._net.start_server(self.settings.listen_port)
                self._controller = Controller(self.settings, self._net)
                self._controller.start()
                self._pumping = True
                self.after(int(1000 / max(1, self.settings.move_rate_hz)), self._pump)
                self.v_status.set(f"streaming on :{self.settings.listen_port}")
            else:
                from .controller import Follower
                self._follower = Follower()
                self._net.connect(self.settings.connect_to, self.settings.listen_port, self._follower.handle)
                self.v_status.set(f"following {self.settings.connect_to}")
            self.btn.config(text="Stop")
        except ImportError:
            self.v_status.set("needs Windows + pywin32")
            self._stop()

    def _pump(self) -> None:
        if self._controller and self._pumping:
            try:
                self._controller.pump()
            except Exception as exc:  # noqa: BLE001
                self.v_status.set(f"error: {exc}")
            self.after(int(1000 / max(1, self.settings.move_rate_hz)), self._pump)

    def _stop(self) -> None:
        self._pumping = False
        if self._controller:
            self._controller.stop(); self._controller = None
        self._follower = None
        if self._net:
            self._net.shutdown(); self._net = None
        self.btn.config(text="Start")
        self.v_status.set("stopped")


def run(settings: Settings, settings_path: Path) -> None:
    root = tk.Tk()
    App(root, settings, settings_path)
    root.mainloop()
