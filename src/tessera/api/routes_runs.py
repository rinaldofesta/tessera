"""Folder-backed live runs plus the legacy sqlite dashboard trends endpoint."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from functools import partial
from pathlib import Path

import anyio
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from tessera.api import responses as R
from tessera.api.schemas import ArchiveRequest
from tessera.api.scrub import scrub_error
from tessera.contract import Run, RunSpec
from tessera.errors import SpecError
from tessera.runner import execute, plan, run_result_payload

router = APIRouter()


@router.post("/api/runs", response_model=Run)
async def start_run(spec: RunSpec, request: Request):
    planned = plan(spec, suites_dir=request.app.state.blueprint_dir)
    if not planned["ready"]:
        raise HTTPException(422, detail=planned["blockers"])

    store = request.app.state.runs
    record = store.create(spec.model_dump())
    job = partial(
        execute,
        record,
        spec.model_dump(),
        store=store,
        suites_dir=request.app.state.blueprint_dir,
        eval_fn=request.app.state.folder_eval_runner,
    )
    queued = run_result_payload(record)
    await request.app.state.schedule(
        anyio.to_thread.run_sync(job)
    )
    # An inline test scheduler may already have completed the store; the launch response
    # remains the coherent queued snapshot captured before scheduling.
    return queued


@router.get("/api/runs", response_model=list[Run])
def list_runs(request: Request, include_archived: bool = False):
    """Run history with verdicts but without heavyweight reports and receipts."""
    return [
        run_result_payload(record, include_report=False)
        for record in request.app.state.runs.list(include_archived=include_archived)
    ]


@router.post("/api/runs/import", response_model=Run)
async def import_run(request: Request, file: UploadFile = File(...)):
    data = await file.read()
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".eval", delete=False) as handle:
            handle.write(data)
            temporary = handle.name
        record = request.app.state.runs.import_log(Path(temporary))
        return run_result_payload(record)
    except Exception as exc:  # noqa: BLE001 — malformed uploads fail at several layers
        raise HTTPException(
            400, detail=scrub_error(f"cannot read log: {type(exc).__name__}: {exc}"),
        ) from exc
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


@router.post("/api/runs/{run_id}/archive", response_model=Run)
def archive_run(run_id: str, request: Request, req: ArchiveRequest = ArchiveRequest()):
    store = request.app.state.runs
    try:
        record = store.get(run_id)
    except SpecError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    if record.data["status"] == "running":
        raise HTTPException(409, "a running evaluation cannot be archived")
    try:
        return run_result_payload(store.set_archived(run_id, req.archived))
    except SpecError as exc:
        raise HTTPException(409, detail=str(exc)) from exc


@router.get("/api/runs/{run_id}", response_model=Run)
def get_run(run_id: str, request: Request):
    try:
        return run_result_payload(request.app.state.runs.get(run_id))
    except SpecError as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@router.get("/api/runs/{run_id}/events")
async def run_events(run_id: str, request: Request):
    """Server-Sent Events stream of run status until terminal. SSE (not WebSocket) is
    simpler and more air-gap-friendly; the FE shows live status off this."""
    from fastapi.responses import StreamingResponse

    try:
        request.app.state.runs.get(run_id)
    except SpecError as exc:
        raise HTTPException(404, detail=str(exc)) from exc

    async def gen():
        for _ in range(600):  # ~10 min ceiling
            try:
                record = request.app.state.runs.get(run_id)
            except SpecError:
                yield f"event: error\ndata: {json.dumps({'error': 'unknown run'})}\n\n"
                return
            status = record.data["status"]
            yield f"data: {json.dumps({'status': status, 'error': record.data['error']})}\n\n"
            if status not in {"queued", "running"}:
                return
            await asyncio.sleep(1)
    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/api/trends", response_model=list[R.TrendPoint])
def trends(request: Request, org: str | None = None, model: str | None = None,
           engine: str | None = None):
    """Time-ordered series across finished runs (optionally filtered) for the dashboard:
    pass^k/mean overall, per-conflict pass^k, and the three axes."""
    out = []
    for row in request.app.state.run_store.finished():
        if org and row["org"] != org:
            continue
        if model and row["model"] != model:
            continue
        if engine and row["judge"] != engine:
            continue
        rep = row["report"]
        if not rep:
            continue
        out.append({
            "id": row["id"], "created_at": row["created_at"],
            "model": row["model"], "org": row["org"], "engine": row["judge"],
            "pass_k_rate": rep["overall"]["pass_k_rate"],
            "mean_rate": rep["overall"]["mean_rate"],
            "categories": {c["key"]: c["pass_k_rate"] for c in rep["categories"]},
            "axes": rep["axes"],
        })
    return out
