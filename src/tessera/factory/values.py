# src/tessera/factory/values.py
"""Hybrid value generators: procedural for clean numeric/date/duration types, curated
anti-prior pools for named types. Every value is type-shaped and verbatim-materializable;
generation is deterministic given the rng. `exclude` lets callers reserve values (e.g. the
canonical published answer) so holdout seeds don't re-expose them."""

from __future__ import annotations

import random
from datetime import date, timedelta

_POOLS: dict[str, list] = {
    "person": ["Dana Okafor", "Marta Villas", "Jonas Brek", "Priya Nair", "Tomas Reuel",
               "Lena Crisp", "Hugo Adeyemi", "Sofia Marchetti"],
    "plan": ["Larkspur", "Juniper", "Marigold", "Cedarwood", "Thornfield", "Hollyhock",
             "Sorrel", "Bramble"],
    "hub": ["Brno", "Gdansk", "Leuven", "Turin", "Aarhus", "Porto", "Vigo", "Kosice"],
    "region": ["Region 4-East", "Region 2-North", "Region 7-West", "Region 5-South",
               "Region 9-Central", "Region 3-East", "Region 6-North"],
    "terms": ["net-30", "net-45", "net-60", "net-15", "net-75", "net-90", "net-21"],
    "data_region": ["EU-Frankfurt", "US-Ohio", "EU-Dublin", "US-Oregon", "APAC-Singapore",
                    "UK-London", "EU-Paris"],
    "month": ["January", "March", "July", "September", "November", "December", "February"],
    "doc_form": ["MSA-2024rev", "MSA-2023r2", "SLA-2025a", "DPA-2024v3", "OF-2025rev",
                 "MSA-2025rev", "DPA-2025v1"],
}


def _money(rng: random.Random):
    if rng.random() < 0.5:
        cents = rng.randrange(105, 595)            # $1.05M .. $5.94M
        if cents % 25 == 0:
            cents += 3
        return f"${cents / 100:.2f}M"
    k = rng.randrange(115, 915)                     # $115k .. $914k
    if k % 25 == 0:
        k += 7
    return f"${k}k"


def _percent(rng: random.Random):
    tenths = rng.randrange(11, 189)                 # 1.1% .. 18.8%
    if tenths % 10 == 0:
        tenths += 3
    return f"{tenths / 10:g}%"


def _date(rng: random.Random):
    return (date(2026, 1, 1) + timedelta(days=rng.randrange(20, 400))).isoformat()


def _duration(rng: random.Random):
    if rng.random() < 0.5:
        return f"{rng.randrange(2, 11)} hours"
    return f"{rng.randrange(35, 175)} minutes"      # off-grid, like meridian's 110 minutes


def _count(rng: random.Random):
    n = rng.randrange(70, 480)
    if n % 10 == 0:
        n += 3
    return n


_PROC = {"money": _money, "percent": _percent, "date": _date,
         "duration": _duration, "count": _count}


def _collides(candidate: str, excluded: set[str]) -> bool:
    """True if `candidate` equals, contains, or is contained by any excluded value.

    Inequality alone is not enough: '2.9%' and '12.9%' are distinct strings, but the
    shorter is a substring of the longer, which empties the downstream substring-based
    distractor filter (evals/dataset._distractor_values) and crashes the invariant
    gates on a fraction of seeds. Rejecting sub/superstrings keeps a conflict pair
    materializable as two genuinely separable values."""
    c = candidate.lower()
    return any(c == e or c in e or e in c for e in excluded)


def gen_value(value_type: str, rng: random.Random, exclude=()):
    """Draw one value of `value_type` that neither equals, contains, nor is contained by
    any value in `exclude` (compared case-insensitively as strings)."""
    excl = {str(e).lower() for e in exclude}
    for _ in range(50):
        v = _PROC[value_type](rng) if value_type in _PROC else rng.choice(_POOLS[value_type])
        if not _collides(str(v), excl):
            return v
    raise RuntimeError(f"could not draw a {value_type} value avoiding {excl}")


def gen_distinct_pair(value_type: str, rng: random.Random, exclude=()):
    """Two distinct values of the same type (the two sides of a conflict)."""
    a = gen_value(value_type, rng, exclude)
    b = gen_value(value_type, rng, tuple(exclude) + (a,))
    return a, b
