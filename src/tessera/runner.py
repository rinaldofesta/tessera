"""Adapters for the shared run payload."""

from __future__ import annotations

from pathlib import Path

from tessera.contract import Run
from tessera.report.compare import diagnose_report
from tessera.store import RunRecord


def _absolute(path) -> str:
    return str(Path(str(path)).resolve())


def _artifact_path(record: RunRecord, name: str) -> str | None:
    path = record.dir.joinpath(name)
    return _absolute(path) if path.is_file() else None


def run_result_payload(record: RunRecord, *, min_pass_k: float | None = None) -> dict:
    """Build the ADR-0002 payload; ``ok`` is operational status, not reliability."""
    data = record.data
    status = data["status"]
    report = record.report()
    receipt = record.receipt()
    verdict = None
    gate = None
    diagnostics: list[dict] = []
    if report is not None:
        overall = report["overall"]
        pass_k_rate = overall["pass_k_rate"]
        mean_rate = overall["mean_rate"]
        if pass_k_rate >= 1:
            label = "reliable"
        elif mean_rate > pass_k_rate:
            label = "inconsistent"
        else:
            label = "unreliable"
        verdict = {
            "pass_k_rate": pass_k_rate,
            "mean_rate": mean_rate,
            "label": label,
        }
        if min_pass_k is not None:
            gate = {"min_pass_k": min_pass_k, "passed": pass_k_rate >= min_pass_k}
        diagnostics = diagnose_report(report)

    payload = Run(
        ok=status in ("queued", "running", "completed"),
        id=record.id,
        status=status,
        source=data["source"],
        archived=data["archived"],
        schema_version=data["schema_version"],
        created_at=data["created_at"],
        started_at=data["started_at"],
        finished_at=data["finished_at"],
        request=data["request"],
        verdict=verdict,
        gate=gate,
        report=report,
        receipt=receipt,
        diagnostics=diagnostics,
        paths={
            "dir": _absolute(record.dir),
            "log": _artifact_path(record, "log.eval"),
            "report_json": _artifact_path(record, "report.json"),
            "report_md": _artifact_path(record, "report.md"),
        },
        error=data["error"],
    )
    return payload.model_dump()
