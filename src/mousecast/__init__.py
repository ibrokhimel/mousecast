"""mousecast -- replicate one PC's mouse to many PCs on the LAN, in real time.

One **controller** PC captures its mouse (movement, clicks, scroll) and streams
it to any number of **follower** PCs on the local network, which reproduce it on
their own screens simultaneously. That is all it does.

Layering keeps the testable logic free of Win32:

  Pure logic (cross-platform, unit-tested):
    screen    -- resolution-independent (0..1) screen coordinates
    protocol  -- mouse-event wire protocol encode/decode
    config    -- settings + JSON
    auth      -- shared-secret HMAC challenge/response

  Networking:
    net       -- asyncio controller(server)/follower(client) + background runner

  Windows layer (pure ctypes, validated on a real Windows box):
    mousehook -- WH_MOUSE_LL capture of move/click/wheel on the controller
    inject    -- reproduce events on a follower (SendInput / SetCursorPos)
    controller-- wires capture -> net (controller) and net -> inject (follower)
    gui       -- tiny Tkinter front end
"""

__version__ = "0.1.0"
