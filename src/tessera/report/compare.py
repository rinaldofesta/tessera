"""Paired, compatibility-aware comparison of Tessera report payloads."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

from tessera.report.stats import exact_mcnemar_p

_DIMENSIONS = (
    "model", "org", "engine", "grader", "k", "scaffold", "seed", "harness",
    "scorer_version", "inspect_ai_version",
)
_INTERVENTIONS = {"model", "org", "engine", "grader", "k", "scaffold", "seed", "harness"}


def _outcomes(report: Mapping[str, Any], prefix: str = "") -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for probe in report.get("probes", []):
        failed = {int(item["epoch"]): item for item in probe.get("failures", [])}
        for epoch in range(1, int(probe.get("epochs_total", 0)) + 1):
            key = f"{prefix}{probe['probe_id']}::{epoch}"
            out[key] = {
                "passed": epoch not in failed,
                "probe_id": str(probe["probe_id"]),
                "epoch": epoch,
                "conflict_type": str(probe.get("conflict_type", "")),
                "failure": failed.get(epoch),
            }
    return out


def diagnose_report(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for probe in report.get("probes", []):
        if 0 < int(probe.get("epochs_passed", 0)) < int(probe.get("epochs_total", 0)):
            counts[("flaky_probe", str(probe["probe_id"]))] += 1
        for failure in probe.get("failures", []):
            if not failure.get("accuracy_ok", True):
                counts[("accuracy", str(probe["probe_id"]))] += 1
            if not failure.get("provenance_ok", True):
                counts[("provenance", str(probe["probe_id"]))] += 1
            if not failure.get("refusal_ok", True):
                counts[("refusal", str(probe["probe_id"]))] += 1
            if failure.get("answer_format_ok") is False:
                counts[("answer_format", str(probe["probe_id"]))] += 1
            for source in failure.get("missing", []):
                counts[("missing_source", str(source))] += 1
    return [
        {"kind": kind, "signature": signature, "count": count}
        for (kind, signature), count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _categorize(outcomes_a: Mapping[str, dict[str, Any]],
                outcomes_b: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    category_keys = sorted(
        {item["conflict_type"] for item in outcomes_a.values()} |
        {item["conflict_type"] for item in outcomes_b.values()}
    )
    categories = []
    for key in category_keys:
        arm_a = {k: value for k, value in outcomes_a.items() if value["conflict_type"] == key}
        arm_b = {k: value for k, value in outcomes_b.items() if value["conflict_type"] == key}
        categories.append({"key": key, **_compare_outcomes(arm_a, arm_b)})
    return categories


def _merge_diagnostics(reports: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for report in reports:
        for item in diagnose_report(report):
            counts[(item["kind"], item["signature"])] += item["count"]
    return [
        {"kind": kind, "signature": signature, "count": count}
        for (kind, signature), count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _compare_outcomes(a: Mapping[str, dict[str, Any]], b: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    shared = sorted(a.keys() & b.keys())
    dropped = sorted(a.keys() ^ b.keys())
    a_wins = sum(1 for key in shared if a[key]["passed"] and not b[key]["passed"])
    b_wins = sum(1 for key in shared if b[key]["passed"] and not a[key]["passed"])
    both_pass = sum(1 for key in shared if a[key]["passed"] and b[key]["passed"])
    both_fail = len(shared) - a_wins - b_wins - both_pass
    return {
        "matched": len(shared),
        "a_wins": a_wins,
        "b_wins": b_wins,
        "both_pass": both_pass,
        "both_fail": both_fail,
        "discordant": a_wins + b_wins,
        "p_value": exact_mcnemar_p(a_wins, b_wins),
        "dropped": dropped,
    }


def compare_reports(report_a: Mapping[str, Any], report_b: Mapping[str, Any],
                    *, intervention: str,
                    receipt_a: Mapping[str, Any] | None = None,
                    receipt_b: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if intervention not in _INTERVENTIONS:
        raise ValueError(f"unknown intervention: {intervention}")
    header_a, header_b = report_a["header"], report_b["header"]
    changed = [name for name in _DIMENSIONS if header_a.get(name) != header_b.get(name)]
    blueprint_a = (receipt_a or {}).get("protocol", {}).get("blueprint_sha256")
    blueprint_b = (receipt_b or {}).get("protocol", {}).get("blueprint_sha256")
    if blueprint_a and blueprint_b and blueprint_a != blueprint_b:
        changed.append("blueprint")
    unexpected = [name for name in changed if name != intervention]
    if intervention not in changed:
        unexpected.append(f"{intervention} did not change")

    outcomes_a, outcomes_b = _outcomes(report_a), _outcomes(report_b)
    overall = _compare_outcomes(outcomes_a, outcomes_b)
    categories = _categorize(outcomes_a, outcomes_b)

    return {
        "compatible": not unexpected,
        "intervention": intervention,
        "changed_dimensions": changed,
        "unexpected_dimensions": unexpected,
        "overall": overall,
        "categories": categories,
        "diagnostics": {"a": diagnose_report(report_a), "b": diagnose_report(report_b)},
    }


def compare_report_sets(reports_a: Iterable[tuple[int, Mapping[str, Any]]],
                        reports_b: Iterable[tuple[int, Mapping[str, Any]]],
                        *, intervention: str) -> dict[str, Any]:
    """Compare repeated run cells, pairing first by repeat and then probe/epoch."""
    by_repeat_a = dict(reports_a)
    by_repeat_b = dict(reports_b)
    shared_repeats = sorted(by_repeat_a.keys() & by_repeat_b.keys())
    if not shared_repeats:
        raise ValueError("the experiment has no completed paired repeats")
    first = compare_reports(by_repeat_a[shared_repeats[0]], by_repeat_b[shared_repeats[0]],
                            intervention=intervention)
    outcomes_a: dict[str, dict[str, Any]] = {}
    outcomes_b: dict[str, dict[str, Any]] = {}
    for repeat in shared_repeats:
        outcomes_a.update(_outcomes(by_repeat_a[repeat], f"{repeat}::"))
        outcomes_b.update(_outcomes(by_repeat_b[repeat], f"{repeat}::"))
    # `overall` must reflect every paired repeat, not just the first — categories and
    # diagnostics were previously left keyed off shared_repeats[0] alone, so a caller
    # trusting them to sum to `overall` (or to represent the whole matrix) silently saw
    # only a fraction of the real paired data whenever repeats > 1.
    first["overall"] = _compare_outcomes(outcomes_a, outcomes_b)
    first["categories"] = _categorize(outcomes_a, outcomes_b)
    first["diagnostics"] = {
        "a": _merge_diagnostics(by_repeat_a[repeat] for repeat in shared_repeats),
        "b": _merge_diagnostics(by_repeat_b[repeat] for repeat in shared_repeats),
    }
    first["paired_repeats"] = shared_repeats
    first["dropped_repeats"] = sorted(by_repeat_a.keys() ^ by_repeat_b.keys())
    return first
