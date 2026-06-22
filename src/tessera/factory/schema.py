# src/tessera/factory/schema.py
"""Declarative slot schema for the meridian variant family: three slot pools, the prose
lexicon, the canonical answers, and an import-time invariant check. This is the single
source of structure the generated (seed != canonical) path draws from."""

from __future__ import annotations

from dataclasses import dataclass

from tessera.models import ConflictType, ResolutionRule

FACTORY_VERSION = "fac-1"  # hand-bumped (like scorer_version "det-4") when the schema,
                           # pools, lexicon, or constructors change generated orgs.

VALUE_TYPES = (
    "money", "percent", "date", "duration", "count", "person", "plan",
    "hub", "region", "terms", "data_region", "month", "doc_form",
)


@dataclass(frozen=True)
class AnswerableSlot:
    """A single-field measurement point; resolvable OR unresolvable per seed."""
    slot_id: str
    probe_id: str
    subject: str
    predicate: str
    question: str
    value_type: str


@dataclass(frozen=True)
class ChainSlot:
    """A `none` cross-silo chain (always `none`). shape in {value_keyed, role_keyed}."""
    slot_id: str
    probe_id: str
    subject: str
    key_predicate: str
    key_value_type: str
    rule_predicate: str
    question: str
    shape: str
    rule_value_type: str | None  # value_keyed: docs-hop type; role_keyed: None
    key_subject_template: str | None  # value_keyed: e.g. "{key} plan"; role_keyed: None
    rule_template: str
    rule_fixed_value: str | None  # role_keyed: e.g. "the account manager"; value_keyed: None


@dataclass(frozen=True)
class VoidSlot:
    """A naturally-absent field; `void` when selected."""
    slot_id: str
    probe_id: str
    subject: str
    predicate: str
    question: str


@dataclass(frozen=True)
class Assignment:
    conflict_type: ConflictType
    resolution_rule: ResolutionRule | None = None
