import pytest

from mousecast.screen import Screen, to_abs, to_norm


def test_center_is_half():
    s = Screen(0, 0, 1920, 1080)
    assert to_norm(960, 540, s) == (0.5, 0.5)


def test_maps_across_different_resolutions():
    a = Screen(0, 0, 1920, 1080)   # controller
    b = Screen(0, 0, 1280, 720)    # follower, smaller
    fx, fy = to_norm(480, 270, a)  # quarter in
    assert (fx, fy) == (0.25, 0.25)
    assert to_abs(fx, fy, b) == (320, 180)  # same quarter on the smaller screen


def test_negative_origin_multimonitor():
    # secondary monitor sitting to the left of the primary
    s = Screen(-1920, 0, 1920, 1080)
    assert to_norm(-960, 540, s) == (0.5, 0.5)
    assert to_abs(0.5, 0.5, s) == (-960, 540)


def test_clamped_to_unit_range():
    s = Screen(0, 0, 100, 100)
    assert to_norm(-50, 200, s) == (0.0, 1.0)   # off-screen clamps
    assert to_abs(2.0, -1.0, s) == (100, 0)


def test_zero_size_rejected():
    with pytest.raises(ValueError):
        to_norm(1, 1, Screen(0, 0, 0, 100))
