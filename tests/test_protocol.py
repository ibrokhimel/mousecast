import math

import pytest

from mousecast.protocol import (
    Button,
    Move,
    ProtocolError,
    Wheel,
    decode,
    encode,
)


@pytest.mark.parametrize(
    "ev",
    [
        Move(0.5, 0.25),
        Move(0.0, 1.0),
        Button(0.5, 0.5, "left", down=True),
        Button(0.1, 0.9, "right", down=False),
        Button(0.3, 0.3, "middle", down=True),
        Wheel(0.5, 0.5, 120),
        Wheel(0.5, 0.5, -240),
    ],
)
def test_round_trip(ev):
    line = encode(ev)
    assert line.endswith("\n")
    got = decode(line)
    assert type(got) is type(ev)
    if isinstance(ev, (Move, Button, Wheel)):
        assert math.isclose(got.fx, ev.fx, abs_tol=1e-6)
        assert math.isclose(got.fy, ev.fy, abs_tol=1e-6)
    if isinstance(ev, Button):
        assert got.button == ev.button and got.down == ev.down
    if isinstance(ev, Wheel):
        assert got.delta == ev.delta


def test_down_up_distinct():
    assert decode("DOWN 0.5 0.5 left").down is True
    assert decode("UP 0.5 0.5 left").down is False


def test_move_format():
    assert encode(Move(0.5, 0.5)) == "MOVE 0.5 0.5\n"


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "JUNK 1 2", "MOVE x y", "DOWN 0.5 0.5 middlebutton", "DOWN 0.5 0.5", "WHEEL 0.1 0.2"],
)
def test_bad_lines_raise(bad):
    with pytest.raises(ProtocolError):
        decode(bad)
