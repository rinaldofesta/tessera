"""Offline acceptance gates for the public reference org (meridian)."""

import json
from collections import Counter

from tessera.compiler import build_artifacts
from tessera.evals.dataset import blueprint_to_dataset
from tessera.examples.meridian_org import build_meridian_blueprint
from tessera.orgs import get_blueprint


def test_meridian_is_registered():
    assert get_blueprint("meridian").probes  # resolves via the ORGS registry


def test_meridian_has_benchmark_resolution():
    # >=5 probes per conflict type: rates must be rates, not one probe's behavior
    bp = build_meridian_blueprint()
    counts = Counter(p.conflict_type.value for p in bp.probes)
    assert all(counts[k] >= 5 for k in ("none", "resolvable", "unresolvable", "void")), counts
    assert len(bp.probes) >= 20
    # both resolution rules exercised — the toy org only covers recency
    rules = {p.resolution_rule.value for p in bp.probes if p.resolution_rule}
    assert rules == {"recency_wins", "authority_wins"}


def test_meridian_authority_probes_invert_recency():
    # the binding doc must be OLDER than the CRM row, or authority_wins tests nothing
    bp = build_meridian_blueprint()
    claims = {c.claim_id: c for c in bp.claims}
    for p in bp.probes:
        if p.resolution_rule and p.resolution_rule.value == "authority_wins":
            ref = [claims[r] for r in p.references]
            binding = max(ref, key=lambda c: c.authority or 0)
            other = min(ref, key=lambda c: c.authority or 0)
            assert binding.authority > other.authority
            assert binding.asserted_at < other.asserted_at  # recency points the wrong way
            assert str(binding.value) == p.expected_answer


def test_meridian_conflict_probes_derive_distractors():
    # det-4 scoring leans on mechanically-derived distractors: they must be non-empty
    # exactly on the answer-probes whose references conflict
    bp = build_meridian_blueprint()
    ds = blueprint_to_dataset(bp)
    by_id = {s.id: s.metadata for s in ds}
    for p in bp.probes:
        meta = by_id[p.probe_id]
        if p.conflict_type.value == "resolvable":
            assert meta["distractor_values"], p.probe_id
        elif p.conflict_type.value == "none":
            assert meta["distractor_values"] == [], p.probe_id


def test_meridian_expected_answers_are_materialized_verbatim():
    # the det engine matches the org's own wording — every expected answer must
    # literally appear in the compiled artifacts (anti-drift gate)
    bp = build_meridian_blueprint()
    art = build_artifacts(bp)
    haystack = json.dumps(art["silos"]) + "\n" + "\n".join(d["content"] for d in art["docs"])
    for p in bp.probes:
        if p.expected_answer:
            assert p.expected_answer in haystack, p.probe_id


def test_meridian_void_questions_have_no_answering_claims():
    # a void probe is only valid if NO claim covers its subject+topic; pin the five
    # (subject, predicate-family) holes so a future claim can't silently break them
    bp = build_meridian_blueprint()
    covered = {(c.subject, c.predicate) for c in bp.claims}
    for subject, predicate in [
        ("Veltrix Labs", "billing_address"),
        ("Halcyon Foods", "executive_sponsor"),
        ("Quill & Quarry", "support_plan"),
        ("Bluepine Logistics", "termination_penalty"),
        ("Tessitura SpA", "seat_count"),
    ]:
        assert (subject, predicate) not in covered


def test_meridian_unresolvable_ties_are_genuinely_symmetric():
    bp = build_meridian_blueprint()
    claims = {c.claim_id: c for c in bp.claims}
    for p in bp.probes:
        if p.conflict_type.value == "unresolvable":
            a, b = (claims[r] for r in p.references)
            assert a.subject == b.subject and a.predicate == b.predicate
            assert a.silo != b.silo                       # cross-silo
            assert a.asserted_at == b.asserted_at         # same timestamp
            assert a.authority == b.authority             # equal authority
            assert str(a.value) != str(b.value)           # and a real disagreement
