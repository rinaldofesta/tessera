# src/tessera/factory/validate.py
"""Property gates for a generated variant — tests/test_meridian_org.py lifted into a
reusable check, plus a `none`-chain join-visibility gate. Runs inside generate_variant
(defense-in-depth) and over many seeds in the suite. Raises VariantInvariantError, so a
construction bug fails loudly instead of silently miscalibrating the benchmark."""

from __future__ import annotations

import json
from collections import Counter

from tessera.compiler import build_artifacts
from tessera.evals.dataset import blueprint_to_dataset
from tessera.factory.schema import SCHEMA
from tessera.models import Blueprint


class VariantInvariantError(AssertionError):
    pass


def _fail(msg: str):
    raise VariantInvariantError(msg)


def assert_variant_invariants(bp: Blueprint) -> None:
    claims = {c.claim_id: c for c in bp.claims}
    probes = bp.probes
    _check_category_resolution(probes)
    _check_authority_inverts_recency(probes, claims)
    _check_distractor_derivation(bp, probes)
    _check_verbatim_materialization(bp, probes)
    _check_void_holes(bp, probes)
    _check_unresolvable_symmetry(probes, claims)
    _check_none_chain_join_visibility(probes, claims)


def _check_category_resolution(probes) -> None:
    counts = Counter(p.conflict_type.value for p in probes)
    if not all(counts[k] >= 5 for k in ("none", "resolvable", "unresolvable", "void")):
        _fail(f"category resolution: {counts}")
    if len(probes) < 20:
        _fail(f"too few probes: {len(probes)}")
    rules = {p.resolution_rule.value for p in probes if p.resolution_rule}
    if rules != {"recency_wins", "authority_wins"}:
        _fail(f"resolution rules present: {rules}")


def _check_authority_inverts_recency(probes, claims) -> None:
    for p in probes:
        if p.resolution_rule and p.resolution_rule.value == "authority_wins":
            ref = [claims[r] for r in p.references]
            binding = max(ref, key=lambda c: c.authority or 0)
            other = min(ref, key=lambda c: c.authority or 0)
            if not (binding.authority > other.authority
                    and binding.asserted_at < other.asserted_at
                    and str(binding.value) == p.expected_answer):
                _fail(f"authority probe not inverting recency: {p.probe_id}")


def _check_distractor_derivation(bp, probes) -> None:
    meta_by_id = {s.id: s.metadata for s in blueprint_to_dataset(bp)}
    for p in probes:
        meta = meta_by_id[p.probe_id]
        if p.conflict_type.value == "resolvable" and not meta["distractor_values"]:
            _fail(f"resolvable probe has no distractors: {p.probe_id}")
        if p.conflict_type.value == "none" and meta["distractor_values"]:
            _fail(f"none probe has spurious distractors: {p.probe_id}")


def _check_verbatim_materialization(bp, probes) -> None:
    art = build_artifacts(bp)
    haystack = json.dumps(art["silos"]) + "\n" + "\n".join(d["content"] for d in art["docs"])
    for p in probes:
        if p.expected_answer and p.expected_answer not in haystack:
            _fail(f"expected answer not materialized: {p.probe_id}")


def _check_void_holes(bp, probes) -> None:
    # no claim may cover a void probe's (subject, predicate)
    covered = {(c.subject, c.predicate) for c in bp.claims}
    void_sp = {v.probe_id: (v.subject, v.predicate) for v in SCHEMA.void_candidates}
    for p in probes:
        if p.conflict_type.value == "void":
            sp = void_sp.get(p.probe_id)
            if sp is None or sp in covered:
                _fail(f"void hole is filled or unknown: {p.probe_id}")


def _check_unresolvable_symmetry(probes, claims) -> None:
    for p in probes:
        if p.conflict_type.value == "unresolvable":
            a, b = (claims[r] for r in p.references)
            if not (a.subject == b.subject and a.predicate == b.predicate and a.silo != b.silo
                    and a.asserted_at == b.asserted_at and a.authority == b.authority
                    and str(a.value) != str(b.value)):
                _fail(f"unresolvable tie not symmetric: {p.probe_id}")


def _check_none_chain_join_visibility(probes, claims) -> None:
    chain_shape = {c.probe_id: c.shape for c in SCHEMA.chains}
    for p in probes:
        if p.conflict_type.value == "none":
            refs = [claims[r] for r in p.references]
            crm = next(c for c in refs if c.silo == "crm")
            docs = next(c for c in refs if c.silo == "docs")
            if chain_shape.get(p.probe_id) == "value_keyed":
                key = str(crm.value)
                rendered = docs.render.template.format(value=docs.value)
                if key not in str(docs.subject) or key not in rendered:
                    _fail(f"none chain decoupled from its key: {p.probe_id}")
            else:  # role_keyed (and canonical's role chain)
                if str(crm.value) != p.expected_answer:
                    _fail(f"role chain answer mismatch: {p.probe_id}")
