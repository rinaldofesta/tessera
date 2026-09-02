# tests/test_factory_schema_inventory.py
from tessera.factory.schema import CANONICAL_ANSWERS, SCHEMA


def test_pool_sizes():
    assert len(SCHEMA.chains) == 6                       # exactly 6 -> none (fixed)
    assert len(SCHEMA.answerable) == 11                  # 6 resolvable + 5 unresolvable
    assert len(SCHEMA.void_candidates) >= 8              # >5 so which 5 are void shuffles


def test_ids_and_subject_predicate_unique():
    ids = [s.slot_id for s in _all(SCHEMA)]
    assert len(ids) == len(set(ids))
    sp = [(s.subject, s.predicate) for s in SCHEMA.answerable] \
        + [(s.subject, s.predicate) for s in SCHEMA.void_candidates] \
        + [(c.subject, c.key_predicate) for c in SCHEMA.chains]
    assert len(sp) == len(set(sp))


def test_slots_by_id_covers_all():
    assert set(SCHEMA.slots_by_id) == {s.slot_id for s in _all(SCHEMA)}


def test_void_predicates_never_answerable():
    answerable_sp = {(s.subject, s.predicate) for s in SCHEMA.answerable}
    chain_sp = {(c.subject, c.key_predicate) for c in SCHEMA.chains}
    for v in SCHEMA.void_candidates:
        assert (v.subject, v.predicate) not in answerable_sp
        assert (v.subject, v.predicate) not in chain_sp


def test_lexicon_covers_every_answerable_predicate_and_framing():
    predicates = {s.predicate for s in SCHEMA.answerable}
    for pred in predicates:
        for framing in ("recency", "authority", "unresolvable"):
            assert (pred, framing) in SCHEMA.lexicon, (pred, framing)
            assert all("{value}" in t for t in SCHEMA.lexicon[(pred, framing)])


def test_canonical_answers_are_answer_bearing_only():
    # 6 none + 6 resolvable = 12 answer-bearing probes carry an expected_answer
    assert len(CANONICAL_ANSWERS) == 12
    assert all(v for v in CANONICAL_ANSWERS.values())


def _all(s):
    return list(s.chains) + list(s.answerable) + list(s.void_candidates)
