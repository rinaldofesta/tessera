# tests/test_factory_construct_singlefield.py
import random
from tessera.factory.construct import construct
from tessera.factory.schema import SCHEMA, Assignment
from tessera.models import ConflictType, ResolutionRule


def _slot(slot_id):
    return SCHEMA.slots_by_id[slot_id]


def test_unresolvable_is_symmetric():
    claims, probes = construct(_slot("ans05"), Assignment(ConflictType.unresolvable),
                              random.Random(2))
    a, b = claims
    assert a.asserted_at == b.asserted_at and a.authority == b.authority
    assert a.silo != b.silo and str(a.value) != str(b.value)
    assert probes[0].expected_behavior.value == "refuse"
    assert probes[0].expected_answer is None
    assert probes[0].expected_sources == [a.claim_id, b.claim_id]


def test_resolvable_recency_newer_wins():
    claims, probes = construct(_slot("ans01"),
                              Assignment(ConflictType.resolvable, ResolutionRule.recency_wins),
                              random.Random(2))
    winner = max(claims, key=lambda c: c.asserted_at)
    assert probes[0].expected_answer == str(winner.value)
    assert probes[0].expected_behavior.value == "answer"


def test_resolvable_authority_older_binding_wins():
    claims, probes = construct(_slot("ans05"),
                              Assignment(ConflictType.resolvable, ResolutionRule.authority_wins),
                              random.Random(2))
    binding = max(claims, key=lambda c: c.authority or 0)
    other = min(claims, key=lambda c: c.authority or 0)
    assert binding.authority > other.authority
    assert binding.asserted_at < other.asserted_at      # recency misleads
    assert probes[0].expected_answer == str(binding.value)


def test_void_emits_no_claims():
    claims, probes = construct(_slot("void1"), Assignment(ConflictType.void), random.Random(2))
    assert claims == []
    assert probes[0].references == [] and probes[0].expected_sources == []
    assert probes[0].expected_behavior.value == "refuse"


def test_winning_value_avoids_canonical_answer():
    from tessera.factory.schema import CANONICAL_ANSWERS
    canon = CANONICAL_ANSWERS["q_orpheon_renewal"]
    for seed in range(1, 40):
        _, probes = construct(_slot("ans01"),
                             Assignment(ConflictType.resolvable, ResolutionRule.recency_wins),
                             random.Random(seed))
        assert probes[0].expected_answer != canon
