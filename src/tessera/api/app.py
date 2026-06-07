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

from fastapi import FastAPI, File, HTTPException, UploadFile
from inspect_ai.log import read_eval_log

from tessera.api.runner import JobRegistry, default_eval_runner, run_eval_job
from tessera.api.schemas import RunRequest
from tessera.report.models import ReportError
from tessera.report.serialize import report_to_dict

_DEFAULT_LOG_DIRS = {"examples": Path("examples"), "logs": Path("logs")}


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
        "created": str(spec.created),
        "k": (spec.config.epochs or 1),
    }


def create_app(eval_runner=default_eval_runner, registry: JobRegistry | None = None,
               log_dirs: dict[str, Path] | None = None, schedule=_background_schedule) -> FastAPI:
    app = FastAPI(title="Tessera Reliability Explorer")
    app.state.registry = registry or JobRegistry()
    app.state.eval_runner = eval_runner
    app.state.log_dirs = log_dirs or _DEFAULT_LOG_DIRS
    app.state.schedule = schedule

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
        registry = app.state.registry
        job_id = registry.create()
        await app.state.schedule(run_eval_job(job_id, req, registry, app.state.eval_runner))
        job = registry.get(job_id)
        return {"job_id": job_id, "status": job.status if job else "running"}

    @app.get("/api/runs/{job_id}")
    def get_run(job_id: str):
        job = app.state.registry.get(job_id)
        if job is None:
            raise HTTPException(404, f"unknown job: {job_id}")
        return {"status": job.status, "report": job.report, "error": job.error}

    return app


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run("tessera.api.app:app", host="127.0.0.1",
                port=int(os.environ.get("TESSERA_API_PORT", "8000")))


if __name__ == "__main__":
    main()
