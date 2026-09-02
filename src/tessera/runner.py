"""Pure planning for Tessera runs; no model calls or filesystem writes."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import ValidationError

from tessera.catalog import resolve_suite
from tessera.contract import Plan, Run, RunSpec
from tessera.errors import SpecError
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


def _validated_spec(spec: dict | RunSpec) -> RunSpec:
    """Shape validation only (defaults, literals, bounds); semantics are blockers.

    Accepts an already-validated RunSpec unchanged (the HTTP route hands one in — it
    was validated once at the FastAPI request boundary and re-running the same
    validation here would just re-derive the identical instance) as well as a plain
    dict (direct/CLI/test callers)."""
    if isinstance(spec, RunSpec):
        return spec
    try:
        return RunSpec.model_validate(spec)
    except ValidationError as exc:
        raise SpecError(str(exc)) from None


def plan(
    spec: dict | RunSpec, *, env: Mapping[str, str] = os.environ,
    suites_dir: Path | None = None,
) -> dict:
    """Return an offline execution plan whose blockers explain how to make it ready."""
    from tessera.api.providers import is_configured, provider_for_model
    from tessera.evals.scoring import SCORER_VERSIONS
    from tessera.evals.task import _SCAFFOLDS

    request = _validated_spec(spec)
    blockers = []
    diagnostics: list[str] = []

    try:
        suite, suite_diagnostics = resolve_suite(request.suite, suites_dir=suites_dir)
        diagnostics.extend(suite_diagnostics)
    except SpecError as exc:
        suite = None
        blockers.append({"code": "unknown_suite", "message": str(exc), "fix": None})

    provider_spec = provider_for_model(request.model)
    provider_id = provider_spec.id if provider_spec else None
    if provider_spec is None:
        blockers.append({
            "code": "unknown_provider",
            "message": f"unknown provider for model '{request.model}'",
            "fix": None,
        })
    elif provider_spec.needs_credentials and not is_configured(provider_spec, env):
        blockers.append({
            "code": "not_connected",
            "message": f"provider '{provider_id}' is not connected",
            "fix": f"tessera connect {provider_id}",
        })

    if request.engine == "llm" and not request.grader:
        blockers.append({
            "code": "grader_required",
            "message": "grader is required when engine is 'llm'",
            "fix": None,
        })
    elif request.engine == "deterministic" and request.grader is not None:
        blockers.append({
            "code": "grader_not_allowed",
            "message": "grader only applies to engine 'llm'",
            "fix": None,
        })
    elif request.grader == request.model:
        blockers.append({
            "code": "self_grading",
            "message": "grader must differ from the model under test",
            "fix": None,
        })

    if request.scaffold not in _SCAFFOLDS:
        blockers.append({
            "code": "unknown_scaffold",
            "message": (
                f"unknown scaffold '{request.scaffold}'; "
                f"available: {', '.join(sorted(_SCAFFOLDS))}"
            ),
            "fix": None,
        })

    return Plan(
        ready=not blockers,
        blockers=blockers,
        diagnostics=diagnostics,
        request=request,
        suite=suite,
        provider=provider_id,
        scorer_version=SCORER_VERSIONS[request.engine],
    ).model_dump()
