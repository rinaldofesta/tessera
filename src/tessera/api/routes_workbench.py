"""Unified evaluation library and evidence-aware report comparisons."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from inspect_ai.log import read_eval_log

from tessera.api import responses as R
from tessera.api.receipts import file_sha256, receipt_from_log, receipt_from_report
from tessera.api.schemas import ComparisonRequest
from tessera.api.scrub import scrub_error
from tessera.report.compare import compare_reports, diagnose_report
from tessera.report.models import ReportError
from tessera.report.serialize import report_to_dict

router = APIRouter()


def _record_log(request: Request, source: str, path: Path) -> None:
    evaluation_id = f"{source}:{path.stem}"
    digest = file_sha256(path)
    existing = request.app.state.workbench_store.get_evaluation(evaluation_id)
    if existing and existing["artifact_sha256"] == digest:
        return
    log = read_eval_log(str(path), resolve_attachments=True)
    report = report_to_dict(log)
    receipt = receipt_from_log(log, report, artifact_sha256=digest)
    request.app.state.workbench_store.record_evaluation(
        evaluation_id=evaluation_id,
        kind="pinned" if source == "examples" else "log",
        source=source,
        source_ref=f"file:{path.resolve()}",
        status="done", report=report, receipt=receipt,
        artifact_path=str(path), artifact_sha256=digest,
    )


def sync_library(request: Request) -> None:
    """Idempotently bring configured .eval directories and legacy API runs into the index."""
    for source, directory in request.app.state.log_dirs.items():
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.eval")):
            try:
                _record_log(request, source, path)
            except Exception:  # noqa: BLE001 — one corrupt artifact must not hide the library
                continue
    # The evaluation library intentionally includes archived runs: it is the durable
    # evidence base; archive governs run-history surfaces.
    for row in request.app.state.run_store.finished(include_archived=True):
        report = row.get("report")
        if not report:
            continue
        receipt = row.get("receipt") or receipt_from_report(report)
        request.app.state.workbench_store.record_evaluation(
            evaluation_id=f"run:{row['id']}", kind="run", source="api",
            source_ref=f"run:{row['id']}", status="done", report=report, receipt=receipt,
            artifact_path=receipt["artifact"]["path"] or None,
            artifact_sha256=receipt["artifact"]["sha256"],
        )


def load_evaluation_report(item: dict, request: Request) -> dict:
    """Resolve evidence from its one authoritative home, never from an index copy."""
    if item.get("report") is not None:  # compatibility with indexes written before 0.3
        return item["report"]
    if item["kind"] == "run" and item["id"].startswith("run:"):
        run = request.app.state.run_store.get(item["id"].split(":", 1)[1])
        if run and run.get("report"):
            return run["report"]
    path = item.get("artifact_path")
    if path and Path(path).is_file():
        return report_to_dict(read_eval_log(path, resolve_attachments=True))
    raise HTTPException(410, f"evaluation evidence is no longer available: {item['id']}")


@router.get("/api/evaluations", response_model=list[R.EvaluationSummary])
def list_evaluations(request: Request):
    sync_library(request)
    return request.app.state.workbench_store.list_evaluations()


@router.get("/api/evaluations/{evaluation_id}/report", response_model=R.Report)
def evaluation_report(evaluation_id: str, request: Request):
    sync_library(request)
    item = request.app.state.workbench_store.get_evaluation(evaluation_id)
    if item is None:
        raise HTTPException(404, f"unknown evaluation: {evaluation_id}")
    return load_evaluation_report(item, request)


@router.post("/api/evaluations/import", status_code=201, response_model=R.EvaluationSummary)
async def import_evaluation(request: Request, file: UploadFile = File(...)):
    data = await file.read()
    import_dir: Path = request.app.state.import_dir
    import_dir.mkdir(parents=True, exist_ok=True)
    evaluation_id = f"import:{uuid.uuid4().hex}"
    destination = import_dir / f"{evaluation_id.split(':', 1)[1]}.eval"
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=import_dir, suffix=".eval", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        log = read_eval_log(tmp_path, resolve_attachments=True)
        report = report_to_dict(log)
    except ReportError as exc:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — the upload itself could not be read
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
        raise HTTPException(400, scrub_error(f"cannot read log: {exc}")) from exc

    # The log parsed cleanly — a failure from here on is a server-side persistence
    # problem, not a bad upload. Reporting it as "cannot read log" would be misleading,
    # and leaving `destination` on disk with no evaluation row indexing it would leak
    # an orphaned file on every retry.
    try:
        os.replace(tmp_path, destination)
        report["header"]["location"] = str(destination)
        digest = file_sha256(destination)
        receipt = receipt_from_log(log, report, artifact_sha256=digest)
        receipt["artifact"]["path"] = str(destination)
        request.app.state.workbench_store.record_evaluation(
            evaluation_id=evaluation_id, kind="import", source="import",
            source_ref=evaluation_id, status="done", report=report, receipt=receipt,
            artifact_path=str(destination), artifact_sha256=digest,
        )
        return request.app.state.workbench_store.get_evaluation(evaluation_id)
    except Exception as exc:  # noqa: BLE001
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(
            500, scrub_error(f"could not index the imported evaluation: {exc}"),
        ) from exc


@router.post("/api/comparisons", response_model=R.ComparisonResult)
def create_comparison(payload: ComparisonRequest, request: Request):
    sync_library(request)
    arm_a = request.app.state.workbench_store.get_evaluation(payload.evaluation_a)
    arm_b = request.app.state.workbench_store.get_evaluation(payload.evaluation_b)
    if arm_a is None:
        raise HTTPException(404, f"unknown evaluation: {payload.evaluation_a}")
    if arm_b is None:
        raise HTTPException(404, f"unknown evaluation: {payload.evaluation_b}")
    try:
        return compare_reports(
            load_evaluation_report(arm_a, request),
            load_evaluation_report(arm_b, request), intervention=payload.intervention,
            receipt_a=arm_a["receipt"], receipt_b=arm_b["receipt"],
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/evaluations/{evaluation_id}/diagnostics", response_model=list[R.Diagnostic])
def evaluation_diagnostics(evaluation_id: str, request: Request):
    sync_library(request)
    item = request.app.state.workbench_store.get_evaluation(evaluation_id)
    if item is None:
        raise HTTPException(404, f"unknown evaluation: {evaluation_id}")
    return diagnose_report(load_evaluation_report(item, request))
