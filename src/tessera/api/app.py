"""FastAPI app: the Tessera Reliability Explorer API.

Endpoints
  GET  /api/logs                 list pinned (examples/) + run (logs/) .eval files
  GET  /api/logs/{id}/report     full report JSON for one log
  POST /api/reports              upload an .eval, get report JSON back
  GET  /api/orgs · /api/models   vocabulary for the Run form (orgs, model choices)
  *    /api/blueprints…          dataset CRUD + validate + compile-preview (key-free)
  POST /api/runs                 start a gated live eval run
  GET  /api/runs[/{job_id}]      history / poll one run (+ /events for SSE)
  GET  /api/trends               time-ordered pass^k series for the dashboard

Handlers live in routes_meta / routes_blueprints / routes_reports / routes_runs and
read their injected seams via request.app.state. Every JSON endpoint declares a
response_model (see responses.py) — the OpenAPI schema they produce is the contract
web/src/api-types.gen.ts is generated from.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

from tessera.api import routes_blueprints, routes_meta, routes_reports, routes_runs
from tessera.api.run_store import RunStore
from tessera.api.runner import default_eval_runner

_DEFAULT_LOG_DIRS = {"examples": Path("examples"), "logs": Path("logs")}
_DEFAULT_BLUEPRINT_DIR = Path("blueprints")
_DEFAULT_RUNS_DB = Path("runs.db")


async def _background_schedule(coro) -> None:
    """Production scheduler: fire-and-forget on the running loop (job stays 'running')."""
    asyncio.create_task(coro)


_LESSON = Path("docs/tessera-lesson.html")


def create_app(eval_runner=default_eval_runner, run_store: RunStore | None = None,
               log_dirs: dict[str, Path] | None = None, schedule=_background_schedule,
               blueprint_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Tessera Reliability Explorer")
    app.state.run_store = run_store or RunStore(_DEFAULT_RUNS_DB)
    app.state.eval_runner = eval_runner
    app.state.log_dirs = log_dirs or _DEFAULT_LOG_DIRS
    app.state.schedule = schedule
    app.state.blueprint_dir = blueprint_dir or _DEFAULT_BLUEPRINT_DIR

    # Registration order IS the OpenAPI path order — the schema is the committed
    # contract (scripts/gen-types.sh), so keep this order stable.
    app.include_router(routes_meta.router)
    app.include_router(routes_blueprints.router)
    app.include_router(routes_reports.router)
    app.include_router(routes_runs.router)

    _mount_learn(app)
    _mount_spa(app)
    return app


def _mount_learn(app: FastAPI, lesson: Path = _LESSON) -> None:
    """Serve the plain-language guide at /learn. Excluded from the OpenAPI schema on
    purpose: it is a static page for humans, not part of the typed contract."""
    from fastapi.responses import FileResponse

    @app.get("/learn", include_in_schema=False)
    def learn():
        if not lesson.exists():
            raise HTTPException(404, "guide not found")
        return FileResponse(lesson, media_type="text/html")


def _mount_spa(app: FastAPI, dist: Path = Path("web/dist")) -> None:
    """If the built React SPA exists, serve it: hashed assets at /assets and an
    index.html fallback for client-side routes. Registered AFTER the /api routes (and
    after FastAPI's /docs, /openapi.json), so they always take precedence."""
    if not dist.exists():
        return
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    assets = dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # Never let the SPA fallback swallow unmatched API routes — keep their 404s honest.
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(404, "not found")
        return FileResponse(dist / "index.html")


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run("tessera.api.app:app", host="127.0.0.1",
                port=int(os.environ.get("TESSERA_API_PORT", "8000")))


if __name__ == "__main__":
    main()
