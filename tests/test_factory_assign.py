# tests/test_factory_assign.py
import random
from collections import Counter
from tessera.factory.assign import assign_conflicts
from tessera.factory.schema import SCHEMA


def _counts(seed):
    asn = assign_conflicts(SCHEMA, random.Random(seed))
    return asn, Counter(a.conflict_type.value for a in asn.values())


def test_counts_are_fixed():
    asn, counts = _counts(11)
    assert len(asn) == 22
    assert counts == {"none": 6, "resolvable": 6, "unresolvable": 5, "void": 5}
    rules = Counter(a.resolution_rule.value for a in asn.values() if a.resolution_rule)
    assert rules == {"recency_wins": 4, "authority_wins": 2}


def test_chains_are_always_none():
    asn, _ = _counts(99)
    for c in SCHEMA.chains:
        assert asn[c.slot_id].conflict_type.value == "none"


def test_deterministic():
    assert assign_conflicts(SCHEMA, random.Random(7)) == assign_conflicts(SCHEMA, random.Random(7))


def test_unresolvable_set_shuffles_across_seeds():
    def unres(seed):
        asn = assign_conflicts(SCHEMA, random.Random(seed))
        return frozenset(k for k, a in asn.items() if a.conflict_type.value == "unresolvable")
    sets = {unres(s) for s in range(1, 30)}
    assert len(sets) > 1   # the refuse set is not fixed
