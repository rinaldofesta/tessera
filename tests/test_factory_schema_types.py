# tests/test_factory_schema_types.py
import dataclasses
import pytest
from tessera.factory.schema import (
    FACTORY_VERSION, VALUE_TYPES, AnswerableSlot, ChainSlot, VoidSlot, Assignment,
)
from tessera.models import ConflictType, ResolutionRule


def test_constants():
    assert FACTORY_VERSION == "fac-1"
    assert len(VALUE_TYPES) == 13 and len(set(VALUE_TYPES)) == 13
    assert "money" in VALUE_TYPES and "doc_form" in VALUE_TYPES


def test_dataclasses_are_frozen():
    a = AnswerableSlot(slot_id="ans01", probe_id="q_x", subject="X", predicate="p",
                       question="?", value_type="money")
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.subject = "Y"


def test_assignment_carries_rule():
    asn = Assignment(ConflictType.resolvable, ResolutionRule.recency_wins)
    assert asn.conflict_type is ConflictType.resolvable
    assert asn.resolution_rule is ResolutionRule.recency_wins
