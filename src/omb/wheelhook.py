"""Global scroll-wheel capture via a WH_MOUSE_LL low-level mouse hook (ctypes).

WINDOWS ONLY. The scroll wheel has no pollable state, so -- unlike clicks, which
OMB detects by polling GetAsyncKeyState -- capturing it requires a low-level
mouse hook. This is the ctypes equivalent of the cffi hook used in the Tcl
version, but ctypes is fully documented and runs under stock Python, so you can
actually test it.

The hook runs its own thread with a message loop (LL hooks require one). The
callback stays tiny: it pushes ``(x, y, delta)`` onto a thread-safe queue and
always passes the event through. Drain the queue from your main loop.

Usage:
    hook = WheelHook()
    hook.start()
    for x, y, delta in hook.drain():
        ...
    hook.stop()
"""
from __future__ import annotations

import queue
import sys
import threading

if sys.platform != "win32":  # pragma: no cover - guarded import
    raise ImportError("omb.wheelhook requires Windows")

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_MOUSE_LL = 14
WM_MOUSEWHEEL = 0x020A
HC_ACTION = 0


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


# LRESULT CALLBACK LowLevelMouseProc(int nCode, WPARAM wParam, LPARAM lParam)
LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.CFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = (wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = (wintypes.HHOOK,)


class WheelHook:
    def __init__(self) -> None:
        self._queue: "queue.Queue[tuple[int, int, int]]" = queue.Queue()
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._hook = None
        # keep a reference so the callback isn't garbage collected while installed
        self._proc = HOOKPROC(self._callback)

    def _callback(self, nCode, wParam, lParam):  # runs in the hook thread
        if nCode == HC_ACTION and wParam == WM_MOUSEWHEEL:
            try:
                ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                delta = ctypes.c_short((ms.mouseData >> 16) & 0xFFFF).value  # signed
                self._queue.put_nowait((ms.pt.x, ms.pt.y, delta))
            except Exception:  # noqa: BLE001 - never let the hook callback throw
                pass
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _run(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        self._hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._proc, None, 0)
        if not self._hook:
            return
        # Standard message pump -- LL hooks are only delivered to a thread with one.
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="omb-wheelhook", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        if self._thread_id:
            WM_QUIT = 0x0012
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            self._thread_id = None

    def drain(self) -> list[tuple[int, int, int]]:
        """Pop all queued wheel events as ``(screen_x, screen_y, delta)`` tuples."""
        out: list[tuple[int, int, int]] = []
        while True:
            try:
                out.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return out
