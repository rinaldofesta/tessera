"""Behavior tests for the Claim / Probe / Blueprint data models.

Each test encodes an invariant from the design spec
(docs/superpowers/specs/2026-06-01-tessera-generator-data-shape-design.md).
"""

import pytest
from pydantic import ValidationError

from tessera.models import (
    Blueprint,
    Claim,
    ConflictType,
    ExpectedBehavior,
    Probe,
    RenderAs,
    ResolutionRule,
)


def _field_claim(**overrides) -> Claim:
    base = dict(
        claim_id="acme.tier.crm",
        subject="Acme Corp",
        predicate="tier",
        value="Gold",
        silo="crm",
        render={"as": "field"},
    )
    base.update(overrides)
    return Claim(**base)


def test_field_claim_constructs_and_exposes_render_as():
    claim = _field_claim()
    assert claim.render.as_ == RenderAs.field


def test_prose_claim_requires_a_template():
    with pytest.raises(ValidationError):
        Claim(
            claim_id="sla.gold.docs",
            subject="Gold tier",
            predicate="sla_hours",
            value=4,
            silo="docs",
            render={"as": "prose"},  # missing template
        )


def test_prose_template_referencing_anything_but_value_is_rejected():
    # the template is rendered with str.format(value=...); a name/index that cannot be
    # filled ({nope}, positional {0}) would raise at compile time, so reject it here
    for bad in ("Renewal is {nope}.", "Renewal is {0}."):
        with pytest.raises(ValidationError):
            _field_claim(value="2026-03-01",
                         render={"as": "prose", "template": bad})
    # a subscript invalid for the actual value is rejected too (an int has no [0])
    with pytest.raises(ValidationError):
        _field_claim(value=7, render={"as": "prose", "template": "Seats: {value[0]}."})
    # a well-formed {value} template still constructs
    ok = _field_claim(value="2026-03-01",
                      render={"as": "prose", "template": "Renewal is {value}."})
    assert ok.render.template == "Renewal is {value}."


def test_refuse_probe_must_not_carry_an_answer():
    with pytest.raises(ValidationError):
        Probe(
            probe_id="p_void",
            question="What is Beta Corp's billing address?",
            references=[],
            conflict_type=ConflictType.void,
            expected_behavior=ExpectedBehavior.refuse,
            expected_answer="123 Main St",  # refusals have no answer
        )


def test_answer_probe_requires_an_answer():
    with pytest.raises(ValidationError):
        Probe(
            probe_id="p_answer",
            question="What is Acme's tier?",
            references=["acme.tier.crm"],
            conflict_type=ConflictType.none,
            expected_behavior=ExpectedBehavior.answer,
            expected_answer=None,  # answers must be present
        )


def test_resolvable_conflict_requires_a_resolution_rule():
    with pytest.raises(ValidationError):
        Probe(
            probe_id="p_conflict",
            question="When is Acme's renewal date?",
            references=["acme.renewal.crm", "acme.renewal.note"],
            conflict_type=ConflictType.resolvable,
            expected_behavior=ExpectedBehavior.answer,
            expected_answer="2026-03-01",  # no resolution_rule given
        )


def test_void_probe_must_have_no_references():
    with pytest.raises(ValidationError):
        Probe(
            probe_id="p_void2",
            question="What is Beta Corp's billing address?",
            references=["acme.tier.crm"],  # a void has no backing claim
            conflict_type=ConflictType.void,
            expected_behavior=ExpectedBehavior.refuse,
        )


def test_valid_resolvable_probe_round_trips():
    probe = Probe(
        probe_id="p_conflict",
        question="When is Acme's renewal date?",
        references=["acme.renewal.crm", "acme.renewal.note"],
        conflict_type=ConflictType.resolvable,
        resolution_rule=ResolutionRule.recency_wins,
        expected_behavior=ExpectedBehavior.answer,
        expected_answer="2026-03-01",
        expected_sources=["acme.renewal.crm", "acme.renewal.note"],
    )
    assert probe.resolution_rule == ResolutionRule.recency_wins
    assert probe.expected_sources == ["acme.renewal.crm", "acme.renewal.note"]


def test_blueprint_rejects_probe_referencing_unknown_claim():
    with pytest.raises(ValidationError):
        Blueprint(
            claims=[_field_claim(claim_id="acme.tier.crm")],
            probes=[
                Probe(
                    probe_id="p",
                    question="?",
                    references=["does.not.exist"],
                    conflict_type=ConflictType.none,
                    expected_behavior=ExpectedBehavior.answer,
                    expected_answer="x",
                )
            ],
        )


def test_blueprint_rejects_expected_source_not_in_claims():
    with pytest.raises(ValidationError):
        Blueprint(
            claims=[_field_claim(claim_id="acme.tier.crm")],
            probes=[
                Probe(
                    probe_id="p",
                    question="?",
                    references=["acme.tier.crm"],
                    conflict_type=ConflictType.none,
                    expected_behavior=ExpectedBehavior.answer,
                    expected_answer="x",
                    expected_sources=["ghost.source"],
                )
            ],
        )


def test_blueprint_rejects_duplicate_claim_ids():
    with pytest.raises(ValidationError):
        Blueprint(
            claims=[
                _field_claim(claim_id="dup"),
                _field_claim(claim_id="dup", predicate="renewal_date", value="2026-01-01"),
            ]
        )


def test_blueprint_accepts_a_consistent_set():
    bp = Blueprint(
        claims=[
            _field_claim(claim_id="acme.tier.crm"),
            _field_claim(
                claim_id="acme.renewal.crm",
                predicate="renewal_date",
                value="2026-01-01",
            ),
        ],
        probes=[
            Probe(
                probe_id="p_ok",
                question="What is Acme's tier?",
                references=["acme.tier.crm"],
                conflict_type=ConflictType.none,
                expected_behavior=ExpectedBehavior.answer,
                expected_answer="Gold",
                expected_sources=["acme.tier.crm"],
            )
        ],
    )
    assert len(bp.claims) == 2 and len(bp.probes) == 1
