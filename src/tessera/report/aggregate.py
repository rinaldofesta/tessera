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
