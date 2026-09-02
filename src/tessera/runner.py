"""Planning and folder-backed execution for Tessera runs."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Mapping
from pathlib import Path

from pydantic import ValidationError

from tessera.api.receipts import file_sha256, receipt_from_log
from tessera.api.scrub import scrub_error
from tessera.catalog import resolve_suite
from tessera.contract import Plan, Run, RunSpec
from tessera.errors import SpecError
from tessera.report.compare import diagnose_report
from tessera.report.render import render_markdown
from tessera.report.serialize import report_to_dict
from tessera.store import RunRecord, RunStore
from tessera.verdict import verdict_of

_EVAL_LOCK = threading.Lock()
_MISSING = object()


def _absolute(path) -> str:
    return str(Path(str(path)).resolve())


def _artifact_path(record: RunRecord, name: str) -> str | None:
    path = record.dir.joinpath(name)
    return _absolute(path) if path.is_file() else None


def run_result_payload(
    record: RunRecord, *, min_pass_k: float | None = None,
    include_report: bool = True,
) -> dict:
    """Build the ADR-0002 payload; ``ok`` is operational status, not reliability."""
    data = record.data
    status = data["status"]
    report = record.report()
    receipt = record.receipt() if include_report else None
    verdict = None
    gate = None
    diagnostics: list[dict] = []
    if report is not None:
        verdict = verdict_of(report)
        if min_pass_k is not None:
            gate = {"min_pass_k": min_pass_k, "passed": verdict["pass_k_rate"] >= min_pass_k}
        if include_report:  # list rows carry the verdict only; details come with the report
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
        report=report if include_report else None,
        receipt=receipt if include_report else None,
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


def _default_eval(**kwargs):
    """Run Inspect with the task function, then re-read its persisted log."""
    import inspect_ai

    from tessera.evals.task import tessera_probes
    from tessera.report.log_adapter import read_log  # inspect_ai loads only when a run starts

    logs = inspect_ai.eval(tessera_probes, **kwargs)
    return read_log(Path(logs[0].location))


def _restore_env(env, name: str, previous) -> None:
    if previous is _MISSING:
        env.pop(name, None)
    else:
        env[name] = previous


def execute(
    record: RunRecord,
    spec: dict,
    *,
    store: RunStore,
    suites_dir: Path,
    eval_fn: Callable[..., object] | None = None,
    env=os.environ,
) -> dict:
    """Execute one run into its folder and always return its final ADR-0002 payload.

    Inspect constructs the task after reading process-global ``TESSERA_OUT`` and
    ``TESSERA_BLUEPRINT_DIR``. A module lock therefore serializes evals in this process;
    runs waiting for it deliberately remain ``queued`` until their eval actually starts.
    """
    try:
        planned = plan(spec, env=env, suites_dir=suites_dir)
        if not planned["ready"]:
            message = "; ".join(blocker["message"] for blocker in planned["blockers"])
            store.mark_failed(record.id, message)
            return run_result_payload(store.get(record.id))

        request = planned["request"]
        suite = planned["suite"]
        run_dir = Path(record.dir)
        runner = eval_fn or _default_eval

        with _EVAL_LOCK:
            store.mark_running(record.id)
            previous_out = env.get("TESSERA_OUT", _MISSING)
            previous_blueprints = env.get("TESSERA_BLUEPRINT_DIR", _MISSING)
            try:
                env["TESSERA_OUT"] = str(run_dir / "org")
                env["TESSERA_BLUEPRINT_DIR"] = str(suites_dir)
                log = runner(
                    model=request["model"],
                    task_args={
                        "judge": request["engine"],
                        "org": suite["org"],
                        "k": request["k"],
                        "scaffold": request["scaffold"],
                        "seed": request["seed"],
                    },
                    log_dir=str(run_dir),
                    display="none",
                    model_roles=(
                        {"grader": request["grader"]} if request["grader"] else None
                    ),
                )
            finally:
                _restore_env(env, "TESSERA_OUT", previous_out)
                _restore_env(env, "TESSERA_BLUEPRINT_DIR", previous_blueprints)

            location = Path(log.location)
            report = report_to_dict(log)
            receipt = receipt_from_log(
                log, report, artifact_sha256=file_sha256(location),
            )
            store.mark_completed(
                record.id,
                report=report,
                receipt=receipt,
                markdown=render_markdown(report),
                log_path=location,
            )
            try:
                if (
                    location.name != "log.eval"
                    and location.resolve().is_relative_to(run_dir.resolve())
                ):
                    location.unlink(missing_ok=True)
            except OSError:
                pass
    except Exception as exc:  # noqa: BLE001 — execution failures are durable run state
        store.mark_failed(record.id, scrub_error(f"{type(exc).__name__}: {exc}"))

    return run_result_payload(store.get(record.id))


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
