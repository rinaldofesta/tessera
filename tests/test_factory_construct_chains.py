# tests/test_factory_construct_chains.py
import random

from tessera.factory.construct import construct
from tessera.factory.schema import SCHEMA, Assignment
from tessera.models import ConflictType


def _slot(slot_id):
    return SCHEMA.slots_by_id[slot_id]


def test_value_keyed_chain_recouples_to_rotated_key():
    # chn01 = Veltrix support_plan -> response_window (value_keyed)
    claims, probes = construct(_slot("chn01"), Assignment(ConflictType.none), random.Random(4))
    crm = next(c for c in claims if c.silo == "crm")
    docs = next(c for c in claims if c.silo == "docs")
    key = str(crm.value)
    rendered = docs.render.template.format(value=docs.value)
    assert key in str(docs.subject)        # docs subject regenerated from the rotated key
    assert key in rendered                  # and the rendered prose
    assert probes[0].expected_answer == str(docs.value)
    # distinct (subject, predicate) -> no spurious distractor
    assert (crm.subject, crm.predicate) != (docs.subject, docs.predicate)


def test_role_keyed_chain_answer_is_crm_value():
    # chn02 = Bluepine account_manager -> renewal_countersigner (role_keyed)
    claims, probes = construct(_slot("chn02"), Assignment(ConflictType.none), random.Random(4))
    crm = next(c for c in claims if c.silo == "crm")
    docs = next(c for c in claims if c.silo == "docs")
    assert probes[0].expected_answer == str(crm.value)        # the person is the answer
    assert docs.value == "the account manager"               # docs references the role
    assert "the account manager" in docs.render.template.format(value=docs.value)


def test_chain_is_deterministic():
    a = construct(_slot("chn04"), Assignment(ConflictType.none), random.Random(9))
    b = construct(_slot("chn04"), Assignment(ConflictType.none), random.Random(9))
    assert [c.value for c in a[0]] == [c.value for c in b[0]]
