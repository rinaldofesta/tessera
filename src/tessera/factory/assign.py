# src/tessera/factory/assign.py
"""Seed -> conflict-type assignment. Canonicalizes (sorts) inputs before consuming the rng,
so the partition is machine-independent. `none` is the fixed 6-chain partition; the
answerable pool shuffles into 5 unresolvable / 6 resolvable (2 authority + 4 recency); the
void pool shuffles to pick which 5 candidates are void."""

from __future__ import annotations

import random

from tessera.factory.schema import Assignment, Schema
from tessera.models import ConflictType, ResolutionRule


def assign_conflicts(schema: Schema, rng: random.Random) -> dict[str, Assignment]:
    out: dict[str, Assignment] = {}

    for chain in schema.chains:                       # fixed: every chain is `none`
        out[chain.slot_id] = Assignment(ConflictType.none)

    answerable = sorted(schema.answerable, key=lambda s: s.slot_id)
    rng.shuffle(answerable)
    for s in answerable[:5]:
        out[s.slot_id] = Assignment(ConflictType.unresolvable)
    resolvable = answerable[5:11]
    for s in resolvable[:2]:
        out[s.slot_id] = Assignment(ConflictType.resolvable, ResolutionRule.authority_wins)
    for s in resolvable[2:]:
        out[s.slot_id] = Assignment(ConflictType.resolvable, ResolutionRule.recency_wins)

    voids = sorted(schema.void_candidates, key=lambda s: s.slot_id)
    rng.shuffle(voids)
    for s in voids[:5]:
        out[s.slot_id] = Assignment(ConflictType.void)

    return out
