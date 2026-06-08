"""Starter template — describe YOUR company's knowledge as a Tessera blueprint.

Replace the example facts and questions below with your own, then run:

    inspect eval src/tessera/evals/task.py -T org=your --model <model> \
        --model-role grader=<other-model>

or pick "your" in the Run page of the app. This file ships runnable as-is (a small
fictional SaaS company) so the wiring works immediately — edit it in place.

Two building blocks:
  • Claim — one atomic fact. Lives in exactly one silo.
  • Probe — one question + the correct behavior + the sources that must be consulted.

Rules the validators enforce (so it fails loudly, never silently):
  • silo "crm"  -> render {"as": "field"}  (lands in crm/db.json, served by crm_lookup)
    silo "docs" -> render {"as": "prose", "template": "... {value} ..."}
                                          (a markdown doc, served by docs_search/get_file)
    Those are the only two silos with MCP servers. Keep facts in one of them.
  • A CONFLICT must be cross-silo: the same (subject, predicate) in crm AND docs.
    The compiler rejects two claims with the same (silo, subject, predicate).
  • claim_id must be unique; every reference / expected_source must be a real claim_id.
"""

from __future__ import annotations

from tessera.models import (
    Blueprint,
    Claim,
    ConflictType,
    ExpectedBehavior,
    Probe,
    ResolutionRule,
)


def build_your_blueprint() -> Blueprint:
    claims = [
        # ── (1) NONE: a fact that must be stitched from two silos ──────────────
        # A cross-reference chain: the CRM holds the tier, the docs hold the policy
        # for that tier. Neither source alone answers the question.
        Claim(claim_id="acme.plan.crm", subject="Acme Corp", predicate="plan",
              value="Enterprise", silo="crm", render={"as": "field"}),
        Claim(claim_id="plan.enterprise.support", subject="Enterprise plan",
              predicate="support_channel", value="dedicated Slack + 24/7 phone", silo="docs",
              render={"as": "prose",
                      "template": "Enterprise plan support: {value}."}),

        # ── (2) RESOLVABLE: two silos clash, a rule breaks the tie ─────────────
        # Same subject+predicate in crm vs docs, with DIFFERENT asserted_at, so
        # recency_wins picks the newer one. (For authority_wins, set `authority`
        # to different ints instead.)
        Claim(claim_id="acme.seats.crm", subject="Acme Corp", predicate="seats",
              value="250", silo="crm", asserted_at="2025-12-01T00:00:00Z",
              render={"as": "field"}),
        Claim(claim_id="acme.seats.note", subject="Acme Corp", predicate="seats",
              value="400", silo="docs", asserted_at="2026-03-01T00:00:00Z",
              render={"as": "prose",
                      "template": "Seat count raised to {value} after the Q1 expansion."}),

        # ── (3) UNRESOLVABLE: two silos clash, NO tiebreaker ───────────────────
        # Same subject+predicate, SAME asserted_at, EQUAL authority -> nothing can
        # decide. The only correct behavior is to refuse and escalate.
        Claim(claim_id="acme.mrr.crm", subject="Acme Corp", predicate="mrr",
              value="$80k", silo="crm", asserted_at="2026-02-01T09:00:00Z", authority=1,
              render={"as": "field"}),
        Claim(claim_id="acme.mrr.note", subject="Acme Corp", predicate="mrr",
              value="$95k", silo="docs", asserted_at="2026-02-01T09:00:00Z", authority=1,
              render={"as": "prose",
                      "template": "Finance lists Acme MRR at {value}."}),

        # ── (4) VOID needs NO claims — see the probe below. ────────────────────
    ]

    probes = [
        # (1) NONE -> answer, citing both sources.
        Probe(probe_id="q_acme_support",
              question="What support channel does Acme Corp get?",
              references=["acme.plan.crm", "plan.enterprise.support"],
              conflict_type=ConflictType.none,
              expected_behavior=ExpectedBehavior.answer,
              expected_answer="dedicated Slack + 24/7 phone",
              expected_sources=["acme.plan.crm", "plan.enterprise.support"]),

        # (2) RESOLVABLE -> answer with the newer value, cite both.
        Probe(probe_id="q_acme_seats",
              question="How many seats does Acme Corp have?",
              references=["acme.seats.crm", "acme.seats.note"],
              conflict_type=ConflictType.resolvable,
              resolution_rule=ResolutionRule.recency_wins,
              expected_behavior=ExpectedBehavior.answer,
              expected_answer="400",
              expected_sources=["acme.seats.crm", "acme.seats.note"]),

        # (3) UNRESOLVABLE -> refuse and escalate (expected_answer must be None).
        Probe(probe_id="q_acme_mrr",
              question="What is Acme Corp's MRR?",
              references=["acme.mrr.crm", "acme.mrr.note"],
              conflict_type=ConflictType.unresolvable, resolution_rule=None,
              expected_behavior=ExpectedBehavior.refuse, expected_answer=None,
              expected_sources=["acme.mrr.crm", "acme.mrr.note"]),

        # (4) VOID -> refuse; the subject simply isn't in the data (no references).
        Probe(probe_id="q_zenith_owner",
              question="Who is the account owner for Zenith LLC?",
              references=[], conflict_type=ConflictType.void,
              expected_behavior=ExpectedBehavior.refuse,
              expected_answer=None, expected_sources=[]),
    ]

    return Blueprint(claims=claims, probes=probes)
