# src/tessera/factory/construct.py
"""Per-conflict-type constructors: turn one slot + its assignment into the 1-2 Claims and
the Probe, with every conflict invariant satisfied by construction. Claim ids use a neutral,
value-independent scheme so a rotated value never leaves a stale identifier echo."""

from __future__ import annotations

import random
from datetime import date, timedelta

from tessera.models import (
    Claim, ConflictType, ExpectedBehavior, Probe, ResolutionRule,
)
from tessera.factory import values
from tessera.factory.schema import (
    SCHEMA, AnswerableSlot, Assignment, CANONICAL_ANSWERS, ChainSlot, VoidSlot,
)

_BASE = date(2026, 1, 1)


def _ts(rng: random.Random, lo: int, hi: int) -> str:
    return (_BASE + timedelta(days=rng.randrange(lo, hi))).isoformat() + "T09:00:00Z"


def _crm(slot_id, subject, predicate, value, *, asserted_at=None, authority=None) -> Claim:
    return Claim(claim_id=f"{slot_id}.crm", subject=subject, predicate=predicate, value=value,
                 silo="crm", asserted_at=asserted_at, authority=authority, render={"as": "field"})


def _docs(slot_id, subject, predicate, value, template, *, asserted_at=None, authority=None) -> Claim:
    return Claim(claim_id=f"{slot_id}.docs", subject=subject, predicate=predicate, value=value,
                 silo="docs", asserted_at=asserted_at, authority=authority,
                 render={"as": "prose", "template": template})


def _pick(predicate: str, framing: str, rng: random.Random) -> str:
    options = SCHEMA.lexicon[(predicate, framing)]
    return options[rng.randrange(len(options))]


def _construct_answerable(slot: AnswerableSlot, asn: Assignment, rng: random.Random):
    canon = CANONICAL_ANSWERS.get(slot.probe_id)
    reserve = (canon,) if canon else ()

    if asn.conflict_type is ConflictType.unresolvable:
        a, b = values.gen_distinct_pair(slot.value_type, rng)
        ts = _ts(rng, 20, 360)
        crm = _crm(slot.slot_id, slot.subject, slot.predicate, a, asserted_at=ts, authority=1)
        tmpl = _pick(slot.predicate, "unresolvable", rng).replace("{subject}", slot.subject)
        docs = _docs(slot.slot_id, slot.subject, slot.predicate, b, tmpl, asserted_at=ts, authority=1)
        probe = Probe(probe_id=slot.probe_id, question=slot.question,
                      conflict_type=ConflictType.unresolvable,
                      references=[crm.claim_id, docs.claim_id],
                      expected_behavior=ExpectedBehavior.refuse, expected_answer=None,
                      expected_sources=[crm.claim_id, docs.claim_id])
        return [crm, docs], [probe]

    # resolvable: pick a winner (avoiding the canonical answer) and a distinct loser
    winner = values.gen_value(slot.value_type, rng, exclude=reserve)
    loser = values.gen_value(slot.value_type, rng, exclude=(*reserve, winner))
    old_ts, new_ts = _ts(rng, 10, 120), _ts(rng, 160, 360)

    if asn.resolution_rule is ResolutionRule.recency_wins:
        crm = _crm(slot.slot_id, slot.subject, slot.predicate, loser, asserted_at=old_ts)
        tmpl = _pick(slot.predicate, "recency", rng).replace("{subject}", slot.subject)
        docs = _docs(slot.slot_id, slot.subject, slot.predicate, winner, tmpl, asserted_at=new_ts)
    else:  # authority_wins: the binding doc is OLDER + higher authority (recency misleads)
        tmpl = _pick(slot.predicate, "authority", rng).replace("{subject}", slot.subject)
        docs = _docs(slot.slot_id, slot.subject, slot.predicate, winner, tmpl,
                     asserted_at=old_ts, authority=3)
        crm = _crm(slot.slot_id, slot.subject, slot.predicate, loser, asserted_at=new_ts, authority=1)

    probe = Probe(probe_id=slot.probe_id, question=slot.question,
                  conflict_type=ConflictType.resolvable, resolution_rule=asn.resolution_rule,
                  references=[crm.claim_id, docs.claim_id],
                  expected_behavior=ExpectedBehavior.answer, expected_answer=str(winner),
                  expected_sources=[crm.claim_id, docs.claim_id])
    return [crm, docs], [probe]


def _construct_void(slot: VoidSlot):
    probe = Probe(probe_id=slot.probe_id, question=slot.question, conflict_type=ConflictType.void,
                  references=[], expected_behavior=ExpectedBehavior.refuse, expected_answer=None,
                  expected_sources=[])
    return [], [probe]


def _construct_chain(slot: ChainSlot, rng: random.Random):
    canon = CANONICAL_ANSWERS.get(slot.probe_id)        # the chain's published answer, if any
    reserve = (canon,) if canon else ()
    if slot.shape == "value_keyed":
        key = values.gen_value(slot.key_value_type, rng)
        rule_val = values.gen_value(slot.rule_value_type, rng, exclude=reserve)  # answer != canonical
        crm = _crm(slot.slot_id, slot.subject, slot.key_predicate, key)
        docs_subject = slot.key_subject_template.replace("{key}", str(key))
        template = slot.rule_template.replace("{key}", str(key))   # leaves {value} for the compiler
        docs = _docs(slot.slot_id, docs_subject, slot.rule_predicate, rule_val, template)
        answer = str(rule_val)
    else:  # role_keyed: the CRM value is the answer; docs references the role abstractly
        person = values.gen_value(slot.key_value_type, rng, exclude=reserve)     # answer != canonical
        crm = _crm(slot.slot_id, slot.subject, slot.key_predicate, person)
        template = slot.rule_template.replace("{subject}", slot.subject)
        docs = _docs(slot.slot_id, slot.subject, slot.rule_predicate, slot.rule_fixed_value, template)
        answer = str(person)
    probe = Probe(probe_id=slot.probe_id, question=slot.question, conflict_type=ConflictType.none,
                  references=[crm.claim_id, docs.claim_id],
                  expected_behavior=ExpectedBehavior.answer, expected_answer=answer,
                  expected_sources=[crm.claim_id, docs.claim_id])
    return [crm, docs], [probe]


def construct(slot, asn: Assignment, rng: random.Random):
    if isinstance(slot, VoidSlot):
        return _construct_void(slot)
    if isinstance(slot, ChainSlot):
        return _construct_chain(slot, rng)
    return _construct_answerable(slot, asn, rng)
