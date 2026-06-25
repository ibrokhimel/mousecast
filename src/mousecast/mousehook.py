"""Capture this PC's mouse globally via a WH_MOUSE_LL low-level hook (ctypes).

WINDOWS ONLY. Captures movement, button presses/releases and the wheel for the
whole desktop. The hook callback stays tiny -- it pushes a normalized event onto
a thread-safe queue and always passes the event through -- and runs on its own
thread with a message loop (LL hooks require one).

Events drained are tuples ``(kind, x, y, arg)`` in absolute screen pixels:
    ("move",  x, y, None)
    ("down",  x, y, "left"|"right"|"middle")
    ("up",    x, y, "left"|"right"|"middle")
    ("wheel", x, y, <signed delta>)
"""
from __future__ import annotations

import queue
import sys
import threading

if sys.platform != "win32":  # pragma: no cover - guarded import
    raise ImportError("mousecast.mousehook requires Windows")

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_MOUSE_LL = 14
HC_ACTION = 0
WM_QUIT = 0x0012

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0201, 0x0202
WM_RBUTTONDOWN, WM_RBUTTONUP = 0x0204, 0x0205
WM_MBUTTONDOWN, WM_MBUTTONUP = 0x0207, 0x0208
WM_MOUSEWHEEL = 0x020A

# msg -> (kind, button)
_BUTTON_EVENTS = {
    WM_LBUTTONDOWN: ("down", "left"),
    WM_LBUTTONUP: ("up", "left"),
    WM_RBUTTONDOWN: ("down", "right"),
    WM_RBUTTONUP: ("up", "right"),
    WM_MBUTTONDOWN: ("down", "middle"),
    WM_MBUTTONUP: ("up", "middle"),
}


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.CFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = (wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = (wintypes.HHOOK,)


class MouseHook:
    def __init__(self) -> None:
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._hook = None
        self._proc = HOOKPROC(self._callback)  # keep a ref so it isn't GC'd

    def _callback(self, nCode, wParam, lParam):  # runs on the hook thread
        if nCode == HC_ACTION:
            try:
                ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                x, y = ms.pt.x, ms.pt.y
                if wParam == WM_MOUSEMOVE:
                    self._queue.put_nowait(("move", x, y, None))
                elif wParam in _BUTTON_EVENTS:
                    kind, button = _BUTTON_EVENTS[wParam]
                    self._queue.put_nowait((kind, x, y, button))
                elif wParam == WM_MOUSEWHEEL:
                    delta = ctypes.c_short((ms.mouseData >> 16) & 0xFFFF).value
                    self._queue.put_nowait(("wheel", x, y, delta))
            except Exception:  # noqa: BLE001 - never let the callback throw
                pass
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _run(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        self._hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._proc, None, 0)
        if not self._hook:
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="mousecast-hook", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            self._thread_id = None

    def drain(self) -> list[tuple]:
        out: list[tuple] = []
        while True:
            try:
                out.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return out
