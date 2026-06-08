"""FastAPI app: the Tessera Reliability Explorer API.

Endpoints
  GET  /api/logs                 list pinned (examples/) + run (logs/) .eval files
  GET  /api/logs/{id}/report     full report JSON for one log
  POST /api/reports              upload an .eval, get report JSON back
  POST /api/runs                 start a gated live eval run
  GET  /api/runs/{job_id}        poll a run; report JSON when done

The report endpoints are pure and key-free. Live runs need model keys (loaded from
.env by the default runner) and run one-at-a-time in a worker thread.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from inspect_ai.log import read_eval_log

import json

from tessera.api import blueprint_store
from tessera.api.run_store import RunStore
from tessera.api.runner import default_eval_runner, run_eval_job
from tessera.api.schemas import RunRequest
from tessera.report.models import ReportError
from tessera.report.serialize import report_to_dict

_DEFAULT_LOG_DIRS = {"examples": Path("examples"), "logs": Path("logs")}
_DEFAULT_BLUEPRINT_DIR = Path("blueprints")
_DEFAULT_RUNS_DB = Path("runs.db")


def _validate_blueprint(data: dict):
    """(blueprint, errors). errors is a structured [{location, message}] from pydantic
    validation AND a dry compile (cross-silo collision) — reusing 100% of existing rules."""
    from pydantic import ValidationError

    from tessera.compiler import build_artifacts
    from tessera.models import Blueprint
    try:
        bp = Blueprint.model_validate(data)
    except ValidationError as exc:
        return None, [{"location": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
                      for e in exc.errors()]
    try:
        build_artifacts(bp)
    except ValueError as exc:
        return None, [{"location": "compile", "message": str(exc)}]
    return bp, []


async def _background_schedule(coro) -> None:
    """Production scheduler: fire-and-forget on the running loop (job stays 'running')."""
    asyncio.create_task(coro)


def _resolve(log_dirs: dict[str, Path], log_id: str) -> Path | None:
    """Map 'source:stem' -> a path inside the whitelisted dir, or None. No traversal."""
    source, _, stem = log_id.partition(":")
    base = log_dirs.get(source)
    if base is None or not stem:
        return None
    candidate = (base / f"{stem}.eval").resolve()
    if base.resolve() not in candidate.parents:
        return None
    return candidate if candidate.exists() else None


def _header_meta(source: str, path: Path) -> dict | None:
    try:
        log = read_eval_log(str(path), header_only=True)
    except Exception:
        return None
    spec = log.eval
    engine = str(spec.task_args.get("judge", "deterministic")) if spec.task_args else "deterministic"
    grader = None
    roles = spec.model_roles or {}
    if engine == "llm" and "grader" in roles:
        gr = roles["grader"]
        grader = getattr(gr, "model", None) or str(gr)
    return {
        "id": f"{source}:{path.stem}",
        "source": source,
        "path": str(path),
        "model": str(spec.model),
        "engine": engine,
        "grader": grader,
        "org": (str(spec.task_args["org"]) if spec.task_args and "org" in spec.task_args else None),
        "created": str(spec.created),
        "k": (spec.config.epochs or 1),
    }


def create_app(eval_runner=default_eval_runner, run_store: RunStore | None = None,
               log_dirs: dict[str, Path] | None = None, schedule=_background_schedule,
               blueprint_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Tessera Reliability Explorer")
    app.state.run_store = run_store or RunStore(_DEFAULT_RUNS_DB)
    app.state.eval_runner = eval_runner
    app.state.log_dirs = log_dirs or _DEFAULT_LOG_DIRS
    app.state.schedule = schedule
    app.state.blueprint_dir = blueprint_dir or _DEFAULT_BLUEPRINT_DIR

    @app.get("/api/orgs")
    def list_orgs():
        """Named blueprints available to run. Raises (500) if a custom org module fails
        to import — the frontend surfaces that as a visible warning rather than letting a
        broken your_org.py silently disappear from the picker."""
        from tessera.examples import org_names
        return org_names()

    # ----- Datasets (blueprints): CRUD + validate + pure compile-preview -----
    # The authoring/validate/preview loop is KEY-FREE (no model calls), so air-gapped
    # users can build and inspect datasets with zero credentials.

    @app.get("/api/blueprints")
    def list_blueprints():
        return blueprint_store.list_blueprints(app.state.blueprint_dir)

    @app.get("/api/blueprints/{blueprint_id}")
    def get_blueprint(blueprint_id: str):
        blueprint_store.seed_from_orgs(app.state.blueprint_dir)  # built-ins fetchable by id
        try:
            bp = blueprint_store.get_blueprint(app.state.blueprint_dir, blueprint_id)
        except blueprint_store.BlueprintStoreError as exc:
            raise HTTPException(400, str(exc))
        if bp is None:
            raise HTTPException(404, f"unknown blueprint: {blueprint_id}")
        return bp.model_dump(by_alias=True)

    @app.post("/api/blueprints/validate")
    def validate_blueprint(blueprint: dict = Body(...)):
        _, errors = _validate_blueprint(blueprint)
        return {"ok": not errors, "errors": errors}

    @app.post("/api/blueprints/preview")
    def preview_blueprint(blueprint: dict = Body(...)):
        """Compile in memory and return the resulting org (CRM db.json, docs, manifest) —
        no disk write, no eval. Powers the editor's live preview."""
        from tessera.compiler import build_artifacts
        bp, errors = _validate_blueprint(blueprint)
        if errors:
            raise HTTPException(400, detail=errors)
        return build_artifacts(bp)

    @app.post("/api/blueprints", status_code=201)
    def create_blueprint(payload: dict = Body(...)):
        blueprint_id = payload.get("id")
        bp, errors = _validate_blueprint(payload.get("blueprint", {}))
        if not blueprint_id:
            raise HTTPException(400, "missing 'id'")
        if errors:
            raise HTTPException(400, detail=errors)
        try:
            if blueprint_store.exists(app.state.blueprint_dir, blueprint_id):
                raise HTTPException(409, f"blueprint '{blueprint_id}' already exists")
            blueprint_store.save_blueprint(app.state.blueprint_dir, blueprint_id, bp)
        except blueprint_store.BlueprintStoreError as exc:
            raise HTTPException(400, str(exc))
        return {"id": blueprint_id}

    @app.put("/api/blueprints/{blueprint_id}")
    def upsert_blueprint(blueprint_id: str, blueprint: dict = Body(...)):
        bp, errors = _validate_blueprint(blueprint)
        if errors:
            raise HTTPException(400, detail=errors)
        try:
            blueprint_store.save_blueprint(app.state.blueprint_dir, blueprint_id, bp)
        except blueprint_store.BlueprintStoreError as exc:
            raise HTTPException(400, str(exc))
        return {"id": blueprint_id}

    @app.delete("/api/blueprints/{blueprint_id}")
    def delete_blueprint(blueprint_id: str):
        try:
            removed = blueprint_store.delete_blueprint(app.state.blueprint_dir, blueprint_id)
        except blueprint_store.BlueprintStoreError as exc:
            raise HTTPException(400, str(exc))
        if not removed:
            raise HTTPException(404, f"unknown blueprint: {blueprint_id}")
        return {"deleted": blueprint_id}

    @app.get("/api/logs")
    def list_logs():
        out = []
        for source, d in app.state.log_dirs.items():
            if not d.exists():
                continue
            for p in sorted(d.glob("*.eval")):
                meta = _header_meta(source, p)
                if meta is not None:
                    out.append(meta)
        return out

    @app.get("/api/logs/{log_id}/report")
    def get_report(log_id: str):
        path = _resolve(app.state.log_dirs, log_id)
        if path is None:
            raise HTTPException(404, f"unknown log id: {log_id}")
        try:
            return report_to_dict(read_eval_log(str(path), resolve_attachments=True))
        except ReportError as exc:
            raise HTTPException(422, str(exc))

    @app.post("/api/reports")
    async def upload_report(file: UploadFile = File(...)):
        data = await file.read()
        with tempfile.NamedTemporaryFile(suffix=".eval", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            return report_to_dict(read_eval_log(tmp_path, resolve_attachments=True))
        except ReportError as exc:
            raise HTTPException(400, str(exc))
        except Exception as exc:                          # noqa: BLE001
            raise HTTPException(400, f"cannot read log: {exc}")
        finally:
            os.unlink(tmp_path)

    @app.post("/api/runs")
    async def start_run(req: RunRequest):
        if req.judge == "llm":
            if not req.grader:
                raise HTTPException(400, "the llm engine requires an independent grader")
            if req.grader == req.model:
                raise HTTPException(
                    400, "grader must differ from the model under test (self-grading guard)")
        store = app.state.run_store
        job_id = store.create(req)
        await app.state.schedule(run_eval_job(job_id, req, store, app.state.eval_runner))
        job = store.get(job_id)
        return {"job_id": job_id, "status": job["status"] if job else "running"}

    @app.get("/api/runs")
    def list_runs():
        """Run history (newest first) with headline rates — for the monitor + dashboard."""
        return app.state.run_store.list()

    @app.get("/api/runs/{job_id}")
    def get_run(job_id: str):
        job = app.state.run_store.get(job_id)
        if job is None:
            raise HTTPException(404, f"unknown job: {job_id}")
        return {"status": job["status"], "report": job["report"], "error": job["error"]}

    @app.get("/api/runs/{job_id}/events")
    async def run_events(job_id: str):
        """Server-Sent Events stream of run status until terminal. SSE (not WebSocket) is
        simpler and more air-gap-friendly; the FE shows live status off this."""
        from fastapi.responses import StreamingResponse

        async def gen():
            for _ in range(600):  # ~10 min ceiling
                job = app.state.run_store.get(job_id)
                if job is None:
                    yield f"event: error\ndata: {json.dumps({'error': 'unknown job'})}\n\n"
                    return
                yield f"data: {json.dumps({'status': job['status'], 'error': job['error']})}\n\n"
                if job["status"] != "running":
                    return
                await asyncio.sleep(1)
        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/api/trends")
    def trends(org: str | None = None, model: str | None = None, engine: str | None = None):
        """Time-ordered series across finished runs (optionally filtered) for the dashboard:
        pass^k/mean overall, per-conflict pass^k, and the three axes."""
        out = []
        for row in app.state.run_store.finished():
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

    return app


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run("tessera.api.app:app", host="127.0.0.1",
                port=int(os.environ.get("TESSERA_API_PORT", "8000")))


if __name__ == "__main__":
    main()
