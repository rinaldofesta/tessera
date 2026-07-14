"""Live eval runs: start (gated), history, poll, SSE stream, and dashboard trends.

Live runs need model keys (loaded from .env by the default runner) and run
one-at-a-time in a worker thread.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request

from tessera.api import responses as R
from tessera.api.runner import run_eval_job
from tessera.api.schemas import RunRequest

router = APIRouter()


@router.post("/api/runs", response_model=R.StartRunResult)
async def start_run(req: RunRequest, request: Request):
    if req.judge == "llm":
        if not req.grader:
            raise HTTPException(400, "the llm engine requires an independent grader")
        if req.grader == req.model:
            raise HTTPException(
                400, "grader must differ from the model under test (self-grading guard)")
    store = request.app.state.run_store
    job_id = store.create(req)
    await request.app.state.schedule(
        run_eval_job(job_id, req, store, request.app.state.eval_runner))
    job = store.get(job_id)
    return {"job_id": job_id, "status": job["status"] if job else "running"}


@router.get("/api/runs", response_model=list[R.RunSummary])
def list_runs(request: Request):
    """Run history (newest first) with headline rates — for the monitor + dashboard."""
    return request.app.state.run_store.list()


@router.get("/api/runs/{job_id}", response_model=R.RunStatus)
def get_run(job_id: str, request: Request):
    job = request.app.state.run_store.get(job_id)
    if job is None:
        raise HTTPException(404, f"unknown job: {job_id}")
    return {"status": job["status"], "report": job["report"], "error": job["error"]}


@router.get("/api/runs/{job_id}/events")
async def run_events(job_id: str, request: Request):
    """Server-Sent Events stream of run status until terminal. SSE (not WebSocket) is
    simpler and more air-gap-friendly; the FE shows live status off this."""
    from fastapi.responses import StreamingResponse

    async def gen():
        for _ in range(600):  # ~10 min ceiling
            job = request.app.state.run_store.get(job_id)
            if job is None:
                yield f"event: error\ndata: {json.dumps({'error': 'unknown job'})}\n\n"
                return
            yield f"data: {json.dumps({'status': job['status'], 'error': job['error']})}\n\n"
            if job["status"] != "running":
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
