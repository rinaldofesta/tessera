"""Paired-contrast statistics for the scaffold intervention. No inspect_ai, no I/O.

The exact McNemar test behind every published significance claim (docs/scaffold.md,
docs/report.md §6, ADR-0009) lives here — tested — rather than inlined in a script:
an edit that changed the tail-doubling convention would silently move published
p-values otherwise.
"""

from __future__ import annotations

from math import comb
from typing import Mapping


def exact_mcnemar_p(b: int, c: int) -> float:
    """Exact two-sided McNemar p over the discordant pairs (a binomial sign test).

    `b` and `c` are the two discordant counts (order irrelevant): under H0 each
    discordant pair is a fair coin, so p = 2 * P(X <= min(b, c)) for
    X ~ Binomial(b + c, 1/2), clamped to 1.0 (the doubled tail overshoots when
    b == c). No discordants at all -> 1.0.
    """
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def format_p(p: float) -> str:
    """Render p at reporting precision, flooring below it — "< 0.0001", never the
    impossible "0.0000" an unguarded {:.4f} produces for an exact test."""
    return f"{p:.4f}" if p >= 1e-4 else "< 0.0001"


def mcnemar_counts(arm_a: Mapping[str, bool],
                   arm_b: Mapping[str, bool]) -> tuple[int, int, tuple[str, ...]]:
    """Pair two arms' pass/fail maps by key.

    Returns (b, c, dropped): b = keys arm_a passes and arm_b fails, c = the reverse,
    dropped = keys present in only one arm, sorted. Callers must surface `dropped` —
    a silently shrunk pairing changes n and therefore the p-value.
    """
    shared = arm_a.keys() & arm_b.keys()
    b = sum(1 for k in shared if arm_a[k] and not arm_b[k])
    c = sum(1 for k in shared if arm_b[k] and not arm_a[k])
    dropped = tuple(sorted((arm_a.keys() | arm_b.keys()) - shared))
    return b, c, dropped
