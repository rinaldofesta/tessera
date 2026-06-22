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
