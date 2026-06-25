import pytest

from omb.geometry import Rect, abs_to_rel, point_in, rel_to_abs


def test_center_maps_to_half():
    r = Rect(x=100, y=200, width=400, height=300)
    assert abs_to_rel(300, 350, r) == (0.5, 0.5)


def test_round_trip_across_differently_sized_windows():
    src = Rect(0, 0, 200, 200)
    dst = Rect(1000, 500, 800, 600)  # different position AND size
    # a click 25% / 75% into the source window
    xp, yp = abs_to_rel(50, 150, src)
    assert (xp, yp) == (0.25, 0.75)
    # must land at the same fraction of the destination window
    assert rel_to_abs(xp, yp, dst) == (1000 + 0.25 * 800, 500 + 0.75 * 600)


def test_corners():
    r = Rect(10, 20, 100, 50)
    assert abs_to_rel(10, 20, r) == (0.0, 0.0)
    assert rel_to_abs(1.0, 1.0, r) == (110, 70)


def test_point_in():
    r = Rect(0, 0, 100, 100)
    assert point_in(0, 0, r)
    assert point_in(99, 99, r)
    assert not point_in(100, 100, r)  # half-open on the far edge
    assert not point_in(-1, 50, r)


def test_zero_size_window_is_rejected():
    with pytest.raises(ValueError):
        abs_to_rel(5, 5, Rect(0, 0, 0, 100))
