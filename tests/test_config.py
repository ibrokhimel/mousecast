from mousecast.config import DEFAULT_PORT, Settings


def test_defaults_round_trip():
    s = Settings()
    assert Settings.from_json(s.to_json()) == s
    assert s.listen_port == DEFAULT_PORT
    assert (s.move, s.clicks, s.wheel) == (True, True, True)


def test_unknown_keys_ignored_missing_default():
    s = Settings.from_dict({"listen_port": 5000, "bogus": 1})
    assert s.listen_port == 5000
    assert s.connect_to == ""  # default


def test_save_load(tmp_path):
    p = tmp_path / "mousecast.json"
    s = Settings(connect_to="192.168.1.10", wheel=False)
    s.save(p)
    assert Settings.load(p) == s


def test_load_missing_returns_defaults(tmp_path):
    assert Settings.load(tmp_path / "nope.json") == Settings()
