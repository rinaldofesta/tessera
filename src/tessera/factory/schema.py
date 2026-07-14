# src/tessera/factory/schema.py
"""Declarative slot schema for the meridian variant family: three slot pools, the prose
lexicon, the canonical answers, and an import-time invariant check. This is the single
source of structure the generated (seed != canonical) path draws from."""

from __future__ import annotations

from dataclasses import dataclass

from tessera.examples.meridian_org import build_meridian_blueprint
from tessera.models import Claim, ConflictType, ResolutionRule

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


# ---- the meridian inventory -----------------------------------------------------------
# Subjects, predicates, and question text are READ OFF the authored org at import time
# (single source: examples/meridian_org.py) — drift between the factory and the authored
# probes is impossible by construction. Only what the generator alone knows (value types,
# chain shapes, prose templates) is declared here, keyed by probe_id.

_CANONICAL_BP = build_meridian_blueprint()
_CANONICAL_PROBES = {p.probe_id: p for p in _CANONICAL_BP.probes}
_CANONICAL_CLAIMS = {c.claim_id: c for c in _CANONICAL_BP.claims}

# canonical published answers, keyed by probe_id (answer-bearing probes only).
CANONICAL_ANSWERS = {
    p.probe_id: p.expected_answer
    for p in _CANONICAL_BP.probes
    if p.expected_answer is not None
}


def _referenced_claims(probe_id: str) -> list[Claim]:
    return [_CANONICAL_CLAIMS[r] for r in _CANONICAL_PROBES[probe_id].references]


def _answerable_slot(slot_id: str, probe_id: str, value_type: str) -> AnswerableSlot:
    # an answerable probe's referenced claims share subject and predicate — any one works
    claim = _referenced_claims(probe_id)[0]
    return AnswerableSlot(slot_id, probe_id, claim.subject, claim.predicate,
                          _CANONICAL_PROBES[probe_id].question, value_type)


def _chain_slot(slot_id: str, probe_id: str, shape: str, key_value_type: str,
                rule_value_type: str | None, key_subject_template: str | None,
                rule_template: str, rule_fixed_value: str | None) -> ChainSlot:
    refs = _referenced_claims(probe_id)
    crm = next(c for c in refs if c.silo == "crm")
    docs = next(c for c in refs if c.silo == "docs")
    return ChainSlot(slot_id, probe_id, crm.subject, crm.predicate, key_value_type,
                     docs.predicate, _CANONICAL_PROBES[probe_id].question, shape,
                     rule_value_type, key_subject_template, rule_template,
                     rule_fixed_value)


_CHAINS = [
    _chain_slot("chn01", "q_veltrix_response", "value_keyed", "plan", "duration",
                "{key} plan",
                "{key} plan tickets get a first response within {value}.", None),
    _chain_slot("chn02", "q_bluepine_countersign", "role_keyed", "person", None, None,
                "{subject} renewal orders are countersigned by {value}.",
                "the account manager"),
    _chain_slot("chn03", "q_halcyon_surcharge", "value_keyed", "terms", "percent",
                "{key} terms",
                "Accounts on {key} terms accrue a {value} monthly surcharge on late invoices.",
                None),
    _chain_slot("chn04", "q_kovacs_hub", "value_keyed", "region", "hub", "{key}",
                "{key} dispatches ship from the {value} hub.", None),
    _chain_slot("chn05", "q_northgate_cap", "value_keyed", "doc_form", "money", "{key}",
                "Under {key} the liability cap is {value} per incident.", None),
    _chain_slot("chn06", "q_arcadia_triage", "value_keyed", "plan", "duration",
                "{key} plan",
                "{key}-plan tickets are triaged within {value}.", None),
]

_ANSWERABLE = [
    _answerable_slot("ans01", "q_orpheon_renewal", "date"),
    _answerable_slot("ans02", "q_veltrix_seats", "count"),
    _answerable_slot("ans03", "q_halcyon_discount", "percent"),
    _answerable_slot("ans04", "q_bluepine_contact", "person"),
    _answerable_slot("ans05", "q_kovacs_value", "money"),
    _answerable_slot("ans06", "q_northgate_region", "data_region"),
    _answerable_slot("ans07", "q_arcadia_value", "money"),
    _answerable_slot("ans08", "q_orpheon_seats", "count"),
    _answerable_slot("ans09", "q_quill_renewal", "date"),
    _answerable_slot("ans10", "q_tessitura_discount", "percent"),
    _answerable_slot("ans11", "q_calder_terms", "terms"),
]

# Void candidates stay literal: only the five the canonical org selects exist as
# authored probes; the other four have no authored counterpart to derive from.
_VOID = [
    VoidSlot("void1", "q_veltrix_billing", "Veltrix Labs", "billing_address",
             "What is Veltrix Labs' billing address?"),
    VoidSlot("void2", "q_halcyon_sponsor", "Halcyon Foods", "executive_sponsor",
             "Who is the executive sponsor for Halcyon Foods?"),
    VoidSlot("void3", "q_quill_plan", "Quill & Quarry", "support_plan",
             "What support plan is Quill & Quarry on?"),
    VoidSlot("void4", "q_bluepine_penalty", "Bluepine Logistics", "termination_penalty",
             "What early-termination penalty applies to Bluepine Logistics?"),
    VoidSlot("void5", "q_tessitura_seats", "Tessitura SpA", "seat_count",
             "How many seats does Tessitura SpA have?"),
    VoidSlot("void6", "q_calder_sponsor", "Calder & Sons", "executive_sponsor",
             "Who is the executive sponsor for Calder & Sons?"),
    VoidSlot("void7", "q_arcadia_billing", "Arcadia Systems", "billing_address",
             "What is Arcadia Systems' billing address?"),
    VoidSlot("void8", "q_kovacs_penalty", "Kovacs Industrial", "termination_penalty",
             "What early-termination penalty applies to Kovacs Industrial?"),
    VoidSlot("void9", "q_orpheon_billing", "Orpheon Group", "billing_address",
             "What is Orpheon Group's billing address?"),
]

# Fixed filler (realistic record width + search noise; never probed). Added to every
# generated variant verbatim, matching meridian's filler so per-field provenance measures
# something real and search returns noise.
_FILLER = [
    Claim(claim_id=f"filler.industry.{i}", subject=subj, predicate="industry",
          value=val, silo="crm", render={"as": "field"})
    for i, (subj, val) in enumerate([
        ("Veltrix Labs", "biotech tooling"), ("Orpheon Group", "media analytics"),
        ("Bluepine Logistics", "cold-chain logistics"), ("Halcyon Foods", "specialty foods"),
        ("Kovacs Industrial", "industrial fasteners"), ("Northgate Medical", "clinical devices"),
        ("Arcadia Systems", "workflow software"), ("Quill & Quarry", "publishing services"),
        ("Tessitura SpA", "textile machinery"), ("Calder & Sons", "marine fittings"),
    ])
] + [
    Claim(claim_id="filler.freeze", subject="Calder & Sons", predicate="deployment_freeze",
          value="December", silo="docs",
          render={"as": "prose",
                  "template": "Calder & Sons observes a deployment freeze each {value}."}),
    Claim(claim_id="filler.escalation", subject="Sev-1 escalations", predicate="page_window",
          value="30 minutes", silo="docs",
          render={"as": "prose",
                  "template": "Sev-1 escalations page the on-call within {value}."}),
    Claim(claim_id="filler.signoff", subject="pricing policy", predicate="signoff_threshold",
          value="3%", silo="docs",
          render={"as": "prose",
                  "template": "Discounts below {value} require CFO sign-off."}),
]

# Prose lexicon: (predicate, framing) -> list of templates, each embedding {value}
# (and optionally {subject}, pre-substituted before compile). One natural binding-document
# noun per predicate for the authority framing.
_AUTH_NOUN = {
    "renewal_date": "signed renewal addendum", "seat_count": "signed capacity addendum",
    "discount_rate": "signed pricing addendum", "primary_contact": "signed account charter",
    "contract_value": "countersigned order form", "data_region": "signed DPA",
    "payment_terms": "signed master agreement",
}
_RECENCY = {
    "renewal_date": ["{subject}'s renewal moved to {value} after the legal review."],
    "seat_count": ["The latest QBR confirmed {subject} is now at {value} seats."],
    "discount_rate": ["Pricing memo: {subject}'s discount stepped to {value} for the new term."],
    "primary_contact": ["Handover note: {value} is now {subject}'s primary contact."],
    "contract_value": ["The revised statement lists {subject}'s contract value as {value}."],
    "data_region": ["Migration note: {subject}'s data now resides in {value}."],
    "payment_terms": ["AP update: {subject} moved to {value} terms this quarter."],
}
_UNRES = {
    "renewal_date": ["Renewal tracker: {subject} renews on {value}."],
    "seat_count": ["Capacity sheet: {subject} is provisioned for {value} seats."],
    "discount_rate": ["Rate card: {subject}'s discount is {value}."],
    "primary_contact": ["Directory: {subject}'s primary contact is {value}."],
    "contract_value": ["Finance tracker: the {subject} contract value stands at {value}."],
    "data_region": ["Infra sheet: {subject} is hosted in {value}."],
    "payment_terms": ["AP note: {subject} pays on {value} terms."],
}


def _build_lexicon():
    lex: dict[tuple[str, str], list[str]] = {}
    for pred in {s.predicate for s in _ANSWERABLE}:
        lex[(pred, "recency")] = list(_RECENCY[pred])
        lex[(pred, "unresolvable")] = list(_UNRES[pred])
        lex[(pred, "authority")] = [
            f"The {_AUTH_NOUN[pred]} sets {{subject}}'s {pred.replace('_', ' ')} at {{value}}; "
            f"it supersedes any CRM estimate."
        ]
    return lex


@dataclass(frozen=True)
class Schema:
    chains: tuple
    answerable: tuple
    void_candidates: tuple
    filler_claims: tuple
    lexicon: dict
    slots_by_id: dict


def _make_schema() -> Schema:
    chains, answerable, void = tuple(_CHAINS), tuple(_ANSWERABLE), tuple(_VOID)
    by_id = {}
    for s in (*chains, *answerable, *void):
        by_id[s.slot_id] = s
    return Schema(chains, answerable, void, tuple(_FILLER), _build_lexicon(), by_id)


SCHEMA = _make_schema()


def _validate_schema() -> None:
    """Fail loudly at import if the schema cannot satisfy the meridian counts or the
    generator's structural assumptions."""
    if len(SCHEMA.chains) != 6:
        raise ValueError(f"need exactly 6 chain slots, got {len(SCHEMA.chains)}")
    if len(SCHEMA.answerable) != 11:
        raise ValueError(f"need exactly 11 answerable slots, got {len(SCHEMA.answerable)}")
    if len(SCHEMA.void_candidates) < 5:
        raise ValueError(f"need >=5 void candidates, got {len(SCHEMA.void_candidates)}")
    ids = [s.slot_id for s in (*SCHEMA.chains, *SCHEMA.answerable, *SCHEMA.void_candidates)]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate slot_id in schema")
    sp = [(s.subject, s.predicate) for s in SCHEMA.answerable] \
        + [(s.subject, s.predicate) for s in SCHEMA.void_candidates] \
        + [(c.subject, c.key_predicate) for c in SCHEMA.chains]
    if len(sp) != len(set(sp)):
        raise ValueError("duplicate (subject, predicate) in schema")
    answerable_sp = {(s.subject, s.predicate) for s in SCHEMA.answerable}
    chain_sp = {(c.subject, c.key_predicate) for c in SCHEMA.chains}
    for v in SCHEMA.void_candidates:
        if (v.subject, v.predicate) in answerable_sp or (v.subject, v.predicate) in chain_sp:
            raise ValueError(f"void candidate {v.slot_id} collides with an answerable field")
    for s in SCHEMA.answerable:
        if s.value_type not in VALUE_TYPES:
            raise ValueError(f"unknown value_type {s.value_type!r}")
        for framing in ("recency", "authority", "unresolvable"):
            templates = SCHEMA.lexicon.get((s.predicate, framing))
            if not templates or any("{value}" not in t for t in templates):
                raise ValueError(f"lexicon missing/invalid ({s.predicate}, {framing})")


_validate_schema()
