# tests/test_factory_commit.py
from tessera.factory.commit import commit, verify
from tessera.factory.schema import FACTORY_VERSION


def test_commit_verify_round_trip():
    commitment, salt = commit(7, FACTORY_VERSION)
    assert verify(commitment, 7, salt, FACTORY_VERSION)


def test_wrong_seed_or_salt_or_version_fails():
    commitment, salt = commit(7, FACTORY_VERSION)
    assert not verify(commitment, 8, salt, FACTORY_VERSION)
    assert not verify(commitment, 7, "00" * 32, FACTORY_VERSION)
    assert not verify(commitment, 7, salt, "fac-999")


def test_salt_is_fresh_each_call():
    _, s1 = commit(7, FACTORY_VERSION)
    _, s2 = commit(7, FACTORY_VERSION)
    assert s1 != s2 and len(s1) == 64        # 32 random bytes, hex


def test_a_malformed_salt_returns_false_not_raises():
    # a verifier handed a non-hex or odd-length salt wants a clean False, not a ValueError
    commitment, _ = commit(7, FACTORY_VERSION)
    assert verify(commitment, 7, "not-hex!!", FACTORY_VERSION) is False
    assert verify(commitment, 7, "abc", FACTORY_VERSION) is False     # odd-length hex
    assert verify(commitment, 7, "", FACTORY_VERSION) is False
