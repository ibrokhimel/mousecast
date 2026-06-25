from omb.config import (
    BroadcastSettings,
    NetworkSettings,
    Settings,
    WindowLayout,
)


def test_defaults_round_trip_through_json():
    s = Settings()
    again = Settings.from_json(s.to_json())
    assert again == s


def test_nested_dataclasses_are_rebuilt_not_left_as_dicts():
    s = Settings()
    s.network.listen = True
    s.network.listen_port = 5000
    s.broadcast.wheel = True
    s.windows = [WindowLayout(10, 20, 800, 600, True)]
    again = Settings.from_json(s.to_json())
    assert isinstance(again.network, NetworkSettings)
    assert isinstance(again.broadcast, BroadcastSettings)
    assert isinstance(again.windows[0], WindowLayout)
    assert again.network.listen_port == 5000
    assert again.broadcast.wheel is True
    assert again.windows[0] == WindowLayout(10, 20, 800, 600, True)


def test_unknown_keys_ignored_and_missing_keys_use_defaults():
    data = {
        "num_windows": 3,
        "totally_unknown_field": 123,
        "network": {"listen_port": 4711, "bogus": True},
    }
    s = Settings.from_dict(data)
    assert s.num_windows == 3
    assert s.network.listen_port == 4711
    assert s.network.listen is False  # missing -> default
    assert s.game == "World of Warcraft"  # missing -> default


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "omb-settings.json"
    s = Settings(num_windows=5)
    s.broadcast.exclude_keys = ["W", "A", "S", "D", "Q", "E"]
    s.save(path)
    loaded = Settings.load(path)
    assert loaded == s


def test_load_missing_file_returns_defaults(tmp_path):
    assert Settings.load(tmp_path / "nope.json") == Settings()
