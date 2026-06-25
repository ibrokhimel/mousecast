"""omb -- an open multiboxing tool for Windows (Python rewrite of OpenMultiBoxing).

Layering (so the testable parts stay free of Win32):

  Pure logic (cross-platform, unit-tested here):
    config     -- typed settings + JSON persistence
    protocol   -- multi-PC wire protocol encode/decode
    geometry   -- absolute<->per-window relative coordinate scaling
    delay      -- per-PC humanization delay model

  Windows layer (needs pywin32/ctypes, validated on a real Windows box):
    winapi     -- thin Win32 wrappers (windows, input, hotkeys)
    wheelhook  -- WH_MOUSE_LL low-level hook to capture the scroll wheel
    net        -- asyncio master/follower sockets (uses protocol + delay)
    broadcast  -- ties capture + injection + net together
    gui        -- Tkinter front end
"""

__version__ = "0.1.0"
