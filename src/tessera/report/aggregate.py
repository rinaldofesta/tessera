"""Pure reductions over ProbeEpoch records. No inspect_ai, no I/O."""

from __future__ import annotations

from collections import defaultdict

from tessera.report.models import (
    AxesSummary, CategoryReliability, ProbeEpoch, ProbeReliability,
)


def reduce_by_probe(records: list[ProbeEpoch]) -> list[ProbeReliability]:
    """Collapse per-epoch records into one ProbeReliability per probe_id."""
    by_id: dict[str, list[ProbeEpoch]] = defaultdict(list)
    for r in records:
        by_id[r.probe_id].append(r)

    out: list[ProbeReliability] = []
    for probe_id, eps in by_id.items():
        eps_sorted = sorted(eps, key=lambda e: e.epoch)
        total = len(eps_sorted)
        passed = sum(1 for e in eps_sorted if e.passed)
        out.append(ProbeReliability(
            probe_id=probe_id,
            conflict_type=eps_sorted[0].conflict_type,
            expected_behavior=eps_sorted[0].expected_behavior,
            epochs_total=total,
            epochs_passed=passed,
            pass_k=(passed == total),
            mean_pass=(passed / total if total else 0.0),
            failures=tuple(e for e in eps_sorted if not e.passed),
        ))
    return out


def aggregate_by(probes: list[ProbeReliability],
                 key=lambda p: p.conflict_type) -> list[CategoryReliability]:
    """Two-level average: group probes by key(), average the binary cliffs and the means.

    `key` is the slicing seam: default conflict_type today; a future field (domain,
    authority_tier, ...) is a one-line lambda swap with zero change to this function.
    """
    buckets: dict[object, list[ProbeReliability]] = defaultdict(list)
    for p in probes:
        buckets[key(p)].append(p)

    out: list[CategoryReliability] = []
    for k, ps in buckets.items():
        n = len(ps)
        out.append(CategoryReliability(
            key=k,
            n_probes=n,
            pass_k_rate=sum(1.0 if p.pass_k else 0.0 for p in ps) / n,
            mean_rate=sum(p.mean_pass for p in ps) / n,
        ))
    return out


def overall_pass_k_rate(probes: list[ProbeReliability]) -> float:
    """Mean over ALL probes of (1.0 if pass_k else 0.0) — the strict headline."""
    if not probes:
        return 0.0
    return sum(1.0 if p.pass_k else 0.0 for p in probes) / len(probes)


def overall_mean_rate(probes: list[ProbeReliability]) -> float:
    """Mean over ALL probes of mean_pass — the consistency annotation beside the headline."""
    if not probes:
        return 0.0
    return sum(p.mean_pass for p in probes) / len(probes)


def summarize_axes(records: list[ProbeEpoch]) -> AxesSummary:
    """Per-axis rates with axis-specific denominators.

    Accuracy is only meaningful where the agent committed (answer-probe-epochs); refusal
    only where it should abstain (refuse-probe-epochs); provenance applies to all. An
    empty denominator yields None (rendered n/a), never a misleading 0%.
    """
    answer = [r for r in records if r.expected_behavior == "answer"]
    refuse = [r for r in records if r.expected_behavior == "refuse"]
    total = len(records)

    def rate(items: list[ProbeEpoch], attr: str) -> float | None:
        if not items:
            return None
        return sum(1 for r in items if getattr(r, attr)) / len(items)

    flagged = [r for r in records if r.answer_format_ok is not None]
    return AxesSummary(
        accuracy_rate=rate(answer, "accuracy_ok"),
        provenance_rate=(sum(1 for r in records if r.provenance_ok) / total) if total else 0.0,
        refusal_rate=rate(refuse, "refusal_ok"),
        n_answer_epochs=len(answer),
        n_refuse_epochs=len(refuse),
        n_total_epochs=total,
        answer_format_rate=rate(flagged, "answer_format_ok"),
    )
