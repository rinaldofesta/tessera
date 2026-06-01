"""A toy two-silo organization exercising the four reliability scenarios."""

from __future__ import annotations

from tessera.models import (
    Blueprint,
    Claim,
    ConflictType,
    ExpectedBehavior,
    Probe,
    ResolutionRule,
)


def build_toy_blueprint() -> Blueprint:
    claims = [
        # Cross-reference chain: tier (CRM) -> SLA (Docs).
        Claim(claim_id="acme.tier.crm", subject="Acme Corp", predicate="tier",
              value="Gold", silo="crm", render={"as": "field"}),
        Claim(claim_id="sla.gold.docs", subject="Gold tier", predicate="sla_hours",
              value=4, silo="docs",
              render={"as": "prose", "template": "Gold-tier SLA is {value} hours."}),
        # Resolvable conflict: stale CRM value vs newer Docs note.
        Claim(claim_id="acme.renewal.crm", subject="Acme Corp", predicate="renewal_date",
              value="2026-01-01", silo="crm", asserted_at="2025-11-15T10:00:00Z",
              render={"as": "field"}),
        Claim(claim_id="acme.renewal.note", subject="Acme Corp", predicate="renewal_date",
              value="2026-03-01", silo="docs", asserted_at="2026-02-10T14:30:00Z",
              render={"as": "prose", "template": "Renewal pushed to {value} per the QBR."}),
        # Unresolvable conflict: same subject+predicate clash across silos, with
        # identical timestamp AND equal authority -> no precedence rule can break it.
        Claim(claim_id="globex.contract.crm", subject="Globex Inc", predicate="contract_value",
              value="$1.2M", silo="crm", asserted_at="2026-02-01T09:00:00Z", authority=1,
              render={"as": "field"}),
        Claim(claim_id="globex.contract.note", subject="Globex Inc", predicate="contract_value",
              value="$1.5M", silo="docs", asserted_at="2026-02-01T09:00:00Z", authority=1,
              render={"as": "prose",
                      "template": "Per the deal desk, the Globex contract value is {value}."}),
    ]
    probes = [
        Probe(
            probe_id="q_acme_sla", question="What is Acme Corp's SLA in hours?",
            references=["acme.tier.crm", "sla.gold.docs"],
            conflict_type=ConflictType.none,
            expected_behavior=ExpectedBehavior.answer, expected_answer="4 hours",
            expected_sources=["acme.tier.crm", "sla.gold.docs"],
        ),
        Probe(
            probe_id="q_acme_renewal", question="When is Acme Corp's renewal date?",
            references=["acme.renewal.crm", "acme.renewal.note"],
            conflict_type=ConflictType.resolvable, resolution_rule=ResolutionRule.recency_wins,
            expected_behavior=ExpectedBehavior.answer, expected_answer="2026-03-01",
            expected_sources=["acme.renewal.crm", "acme.renewal.note"],
        ),
        Probe(
            probe_id="q_globex_contract", question="What is Globex Inc's contract value?",
            references=["globex.contract.crm", "globex.contract.note"],
            conflict_type=ConflictType.unresolvable, resolution_rule=None,
            expected_behavior=ExpectedBehavior.refuse,
            expected_answer=None,
            expected_sources=["globex.contract.crm", "globex.contract.note"],
        ),
        Probe(
            probe_id="q_beta_billing", question="What is Beta Corp's billing address?",
            references=[], conflict_type=ConflictType.void,
            expected_behavior=ExpectedBehavior.refuse,
            expected_answer=None, expected_sources=[],
        ),
    ]
    return Blueprint(claims=claims, probes=probes)
