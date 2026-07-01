"""Pure JSON serialization of a Tessera report. No inspect_ai, no I/O.

Mirrors `report.cli._build_report` exactly, but returns a JSON-native dict instead of
Markdown so the API and the Markdown scorecard never diverge. The category order, the
`flaky` flag, and the per-failure `missing` set are computed identically to `render.py`.
"""

from __future__ import annotations

from tessera.report.aggregate import (
    aggregate_by, overall_mean_rate, overall_pass_k_rate, reduce_by_probe, summarize_axes,
)
from tessera.report.log_adapter import eval_log_to_records
from tessera.report.models import CANONICAL_ORDER, ProbeEpoch, ProbeReliability


def _epoch_to_dict(e: ProbeEpoch) -> dict:
    return {
        "epoch": e.epoch,
        "passed": e.passed,
        "accuracy_ok": e.accuracy_ok,
        "provenance_ok": e.provenance_ok,
        "refusal_ok": e.refusal_ok,
        "question": e.question,
        "answer": e.answer,
        "consulted": list(e.consulted),
        "expected_sources": list(e.expected_sources),
        "missing": sorted(set(e.expected_sources) - set(e.consulted)),
        "answer_format_ok": e.answer_format_ok,
    }


def _probe_to_dict(p: ProbeReliability) -> dict:
    return {
        "probe_id": p.probe_id,
        "conflict_type": p.conflict_type,
        "expected_behavior": p.expected_behavior,
        "epochs_total": p.epochs_total,
        "epochs_passed": p.epochs_passed,
        "pass_k": p.pass_k,
        "mean_pass": p.mean_pass,
        "failures": [_epoch_to_dict(e) for e in p.failures],
    }


def report_to_dict(log) -> dict:
    """Same pipeline as cli._build_report, serialized to a JSON-native dict."""
    header, records = eval_log_to_records(log)
    probes = reduce_by_probe(records)
    by_key = {c.key: c for c in aggregate_by(probes)}
    axes = summarize_axes(records)

    categories = []
    for key in CANONICAL_ORDER:
        c = by_key.get(key)
        if c is None:
            continue
        categories.append({
            "key": c.key,
            "n_probes": c.n_probes,
            "pass_k_rate": c.pass_k_rate,
            "mean_rate": c.mean_rate,
            "flaky": c.mean_rate > c.pass_k_rate,
        })

    order = {ct: i for i, ct in enumerate(CANONICAL_ORDER)}
    probes_sorted = sorted(probes, key=lambda p: (order.get(p.conflict_type, 99), p.probe_id))

    return {
        "header": {
            "model": header.model,
            "engine": header.engine,
            "grader": header.grader,
            "org": header.org,
            "k": header.k,
            "created": header.created,
            "location": header.location,
            "scorer_version": header.scorer_version,
            "inspect_ai_version": header.inspect_ai_version,
            "scaffold": header.scaffold,
            "seed": header.seed,
        },
        "overall": {
            "pass_k_rate": overall_pass_k_rate(probes),
            "mean_rate": overall_mean_rate(probes),
        },
        "categories": categories,
        "axes": {
            "accuracy_rate": axes.accuracy_rate,
            "provenance_rate": axes.provenance_rate,
            "refusal_rate": axes.refusal_rate,
            "n_answer_epochs": axes.n_answer_epochs,
            "n_refuse_epochs": axes.n_refuse_epochs,
            "n_total_epochs": axes.n_total_epochs,
            "answer_format_rate": axes.answer_format_rate,
        },
        "probes": [_probe_to_dict(p) for p in probes_sorted],
    }
