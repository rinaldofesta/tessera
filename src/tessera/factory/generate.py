# src/tessera/factory/generate.py
"""generate_variant(seed): the deterministic, key-free entry point. seed == CANONICAL_SEED
delegates to the authored meridian (baseline preserved); other seeds re-deal the conflict
graph and synthesize fresh values, validated by the property gates."""

from __future__ import annotations

import random

from tessera.examples.meridian_org import build_meridian_blueprint
from tessera.factory.assign import assign_conflicts
from tessera.factory.construct import construct
from tessera.factory.schema import SCHEMA
from tessera.factory.validate import assert_variant_invariants
from tessera.models import Blueprint

CANONICAL_SEED = 0


def generate_variant(seed: int) -> Blueprint:
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError(f"seed must be a non-negative int, got {seed!r}")
    if seed == CANONICAL_SEED:
        return build_meridian_blueprint()              # pinned authored draw — exact

    rng = random.Random(seed)
    assignment = assign_conflicts(SCHEMA, rng)         # exactly the 22 selected slots
    claims = list(SCHEMA.filler_claims)
    probes = []
    for slot_id in sorted(assignment):                 # canonical order; rng already seeded assign
        slot = SCHEMA.slots_by_id[slot_id]
        c, p = construct(slot, assignment[slot_id], rng)
        claims += c
        probes += p

    bp = Blueprint(claims=claims, probes=probes)       # Pydantic validators fire here
    assert_variant_invariants(bp)                      # defense-in-depth
    return bp
