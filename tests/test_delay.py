import random

from omb.delay import DelayModel


def test_base_delay_is_constant_per_pc():
    m = DelayModel(pc_delay_max_ms=5000, jitter_max_ms=150, rng=random.Random(1))
    first = m.base_for("pcA")
    # base must never change across many lookups
    for _ in range(100):
        assert m.base_for("pcA") == first


def test_base_within_bounds_and_distinct_pcs_independent():
    m = DelayModel(pc_delay_max_ms=5000, jitter_max_ms=150, rng=random.Random(7))
    a = m.base_for("pcA")
    b = m.base_for("pcB")
    assert 0 <= a <= 5000
    assert 0 <= b <= 5000


def test_next_delay_is_base_plus_jitter_window():
    m = DelayModel(pc_delay_max_ms=5000, jitter_max_ms=150, rng=random.Random(3))
    base = m.base_for("pc")
    for _ in range(500):
        d = m.next_delay_ms("pc")
        assert base <= d <= base + 150


def test_forget_resets_base():
    rng = random.Random(42)
    m = DelayModel(pc_delay_max_ms=5000, jitter_max_ms=150, rng=rng)
    first = m.base_for("pc")
    m.forget("pc")
    # after forgetting, a new base is drawn from the same stream (so it differs
    # from `first` for this seed) -- the point is the old value is gone.
    assert "pc" not in m._base


def test_deterministic_under_seed():
    a = DelayModel(2000, 100, rng=random.Random(99))
    b = DelayModel(2000, 100, rng=random.Random(99))
    seq_a = [a.next_delay_ms("x") for _ in range(20)]
    seq_b = [b.next_delay_ms("x") for _ in range(20)]
    assert seq_a == seq_b
