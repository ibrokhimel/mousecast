import math

import pytest

from omb.protocol import (
    KeyMsg,
    MouseMsg,
    ProtocolError,
    WheelMsg,
    decode,
    encode,
    is_mouse_like,
)


@pytest.mark.parametrize(
    "msg",
    [
        MouseMsg(0.5, 0.25, "left"),
        MouseMsg(0.0, 1.0, "right"),
        MouseMsg(0.123456, 0.987654, ""),  # a move (no button)
        WheelMsg(0.5, 0.5, 120),
        WheelMsg(0.5, 0.5, -120),
        KeyMsg(down=True, keycode=65),
        KeyMsg(down=False, keycode=0x57),
    ],
)
def test_round_trip(msg):
    line = encode(msg)
    assert line.endswith("\n")
    got = decode(line)
    if isinstance(msg, (MouseMsg, WheelMsg)):
        assert math.isclose(got.xp, msg.xp, rel_tol=0, abs_tol=1e-9)
        assert math.isclose(got.yp, msg.yp, rel_tol=0, abs_tol=1e-9)
    assert got == msg or isinstance(msg, (MouseMsg, WheelMsg))


def test_move_has_no_button_token():
    assert encode(MouseMsg(0.5, 0.5, "")) == "MOUSE 0.5 0.5\n"


def test_decode_move_vs_click():
    assert decode("MOUSE 0.5 0.5\n").button == ""
    assert decode("MOUSE 0.5 0.5 left\n").button == "left"


def test_wheel_delta_is_int_and_signed():
    assert decode("WHEEL 0.1 0.2 -240\n") == WheelMsg(0.1, 0.2, -240)


def test_keys_are_not_mouse_like_but_mouse_and_wheel_are():
    assert is_mouse_like(MouseMsg(0, 0))
    assert is_mouse_like(WheelMsg(0, 0, 120))
    assert not is_mouse_like(KeyMsg(down=True, keycode=65))


@pytest.mark.parametrize("bad", ["", "   ", "NONSENSE 1 2", "MOUSE x y", "WHEEL 0.1 0.2", "DOWN"])
def test_bad_lines_raise(bad):
    with pytest.raises(ProtocolError):
        decode(bad)
