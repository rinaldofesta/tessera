"""One user-facing reliability verdict, shared by every Tessera surface."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CONFLICT_LABELS = {
    "none": "sources agree",
    "resolvable": "conflict, tiebreaker applies",
    "unresolvable": "genuine disagreement",
    "void": "fact missing",
}


def counts_of(report: Mapping[str, Any]) -> dict[str, int]:
    """Count probes by the reliability statement their repeated outcomes support.

    One pass, and the three counts are mutually exclusive by construction (every probe
    lands in exactly one bucket) rather than three independent predicates that could
    theoretically double- or undercount the same probe.
    """
    every_time = never = total = 0
    for probe in report.get("probes", []):
        total += 1
        if probe.get("pass_k") == 1:
            every_time += 1
        elif probe.get("mean_pass") == 0:
            never += 1
    return {
        "total": total,
        "every_time": every_time,
        "sometimes": total - every_time - never,
        "never": never,
    }


def trouble_spot(report: Mapping[str, Any]) -> str | None:
    """Return the plain-language label for the least reliable category."""
    candidates = [
        category
        for category in report.get("categories", [])
        if category.get("pass_k_rate", 1) < 1
    ]
    if not candidates:
        return None
    key = min(candidates, key=lambda category: category["pass_k_rate"])["key"]
    return CONFLICT_LABELS.get(key, key)


def _questions(count: int) -> str:
    return "question" if count == 1 else "questions"


def _clause(count: int, phrase: str) -> str | None:
    if not count:
        return None
    verb = "is" if count == 1 else "are"
    return f"{count} {_questions(count)} {verb} {phrase}."


def sentence(report: Mapping[str, Any]) -> str:
    """Describe a report's reliability in one stable, user-facing sentence."""
    counts = counts_of(report)
    total = counts["total"]
    every_time = counts["every_time"]
    # total > 0 as well as every_time == total: a report with zero probes must not read
    # as "Reliable." while verdict_of()'s label — computed independently from
    # report['overall'], which is 0.0/0.0 for zero probes — comes out "unreliable".
    reliable = total > 0 and every_time == total
    if reliable:
        parts = [
            "Reliable.",
            f"Right every time on all {total} {_questions(total)}.",
        ]
    else:
        parts = [
            "Not reliable.",
            f"Right every time on {every_time} of {total} {_questions(total)}.",
        ]

    for clause in (
        _clause(counts["sometimes"], "right only sometimes"),
        _clause(counts["never"], "never right"),
    ):
        if clause:
            parts.append(clause)

    if spot := trouble_spot(report):
        parts.append(f"Trouble spot: {spot}.")
    return " ".join(parts)


def verdict_of(report: Mapping[str, Any]) -> dict[str, Any]:
    """The payload's verdict block. reliable = every probe right every time; inconsistent =
    some repeats pass (mean > pass^k) — the flakiness Tessera exists to surface;
    unreliable = fails the same way every time. Same rule as the UI's VerdictBadge."""
    overall = report["overall"]
    pass_k_rate = overall["pass_k_rate"]
    mean_rate = overall["mean_rate"]
    if pass_k_rate >= 1:
        label = "reliable"
    elif mean_rate > pass_k_rate:
        label = "inconsistent"
    else:
        label = "unreliable"
    return {
        "pass_k_rate": pass_k_rate,
        "mean_rate": mean_rate,
        "label": label,
        "sentence": sentence(report),
    }
