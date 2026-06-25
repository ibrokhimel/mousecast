from mousecast.auth import make_nonce, sign, verify


def test_correct_secret_verifies():
    nonce = make_nonce()
    assert verify("hunter2", nonce, sign("hunter2", nonce))


def test_wrong_secret_rejected():
    nonce = make_nonce()
    assert not verify("hunter2", nonce, sign("wrong", nonce))


def test_replay_with_different_nonce_fails():
    response = sign("s3cret", make_nonce())  # captured response for an old nonce
    fresh = make_nonce()
    assert not verify("s3cret", fresh, response)


def test_nonces_are_unique_and_nonempty():
    nonces = {make_nonce() for _ in range(1000)}
    assert len(nonces) == 1000
    assert all(n for n in nonces)


def test_empty_secret_is_consistent_open_mode():
    nonce = make_nonce()
    # both ends with empty secret still agree (open LAN mode)
    assert verify("", nonce, sign("", nonce))
    # but a non-empty secret won't match an empty-secret peer
    assert not verify("", nonce, sign("x", nonce))


def test_response_whitespace_tolerated():
    nonce = make_nonce()
    assert verify("k", nonce, sign("k", nonce) + "\n")
