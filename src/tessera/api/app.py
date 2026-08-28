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
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from tessera.api import (
    routes_blueprints,
    routes_meta,
    routes_providers,
    routes_reports,
    routes_runs,
)
from tessera.api.run_store import RunStore
from tessera.api.runner import default_eval_runner

_DEFAULT_LOG_DIRS = {"examples": Path("examples"), "logs": Path("logs")}
_DEFAULT_BLUEPRINT_DIR = Path("blueprints")
_DEFAULT_RUNS_DB = Path("runs.db")
_DEFAULT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def _resolve_env_file(env_file: Path | None) -> Path:
    """One authoritative absolute path. Resolved, never read, at construction time."""
    override = os.environ.get("TESSERA_ENV_FILE")
    chosen = env_file or (Path(override) if override else _DEFAULT_ENV_FILE)
    return Path(chosen).resolve()


def _build_discovery_cache():
    """Wire the three sources behind one cache. httpx is imported lazily so importing
    the app stays cheap and the key-free test suite never opens a client it won't use."""
    from tessera.api.discovery.cache import DiscoveryCache
    from tessera.api.discovery.cloud import discover_cloud
    from tessera.api.discovery.merge import merge
    from tessera.api.discovery.mlx import discover_mlx
    from tessera.api.discovery.ollama import discover_ollama

    def collect():
        import httpx
        hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
        with httpx.Client() as client:
            results = [
                discover_cloud(client, env=os.environ),
                discover_ollama(client),
                discover_mlx(client, hf_home=hf_home,
                             base_url=os.environ.get("MLX_BASE_URL")),
            ]
        # The curated list is routes_meta's TESSERA_MODELS-or-defaults resolution —
        # imported here rather than duplicated, so the two cannot drift.
        from tessera.api.routes_meta import _resolved_models
        return merge(results, curated=_resolved_models())

    return DiscoveryCache(collect=collect)


async def _background_schedule(coro) -> None:
    """Production scheduler: fire-and-forget on the running loop (job stays 'running')."""
    asyncio.create_task(coro)


_LESSON = Path("docs/tessera-lesson.html")


def create_app(eval_runner=default_eval_runner, run_store: RunStore | None = None,
               log_dirs: dict[str, Path] | None = None, schedule=_background_schedule,
               blueprint_dir: Path | None = None, env_file: Path | None = None) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # interpolate=False: dotenv expands ${VAR} inside BOTH quoting styles, which
        # would corrupt any credential containing "${". Credentials are literals.
        # override=False: a variable already exported in the shell wins over the file.
        try:
            from dotenv import load_dotenv
            load_dotenv(app.state.env_file, interpolate=False, override=False)
        except ImportError:
            pass
        yield

    app = FastAPI(title="Tessera Reliability Explorer", lifespan=lifespan)
    app.state.run_store = run_store or RunStore(_DEFAULT_RUNS_DB)
    app.state.eval_runner = eval_runner
    app.state.log_dirs = log_dirs or _DEFAULT_LOG_DIRS
    app.state.schedule = schedule
    app.state.blueprint_dir = blueprint_dir or _DEFAULT_BLUEPRINT_DIR
    app.state.env_file = _resolve_env_file(env_file)
    app.state.discovery_cache = _build_discovery_cache()

    @app.exception_handler(RequestValidationError)
    def _sanitized_validation_error(request: Request, exc: RequestValidationError):
        # pydantic puts the rejected value in `input` (and sometimes `ctx`), so the
        # default 422 hands a submitted credential straight back. Keep the location
        # and the reason; drop anything derived from the submission itself.
        return JSONResponse(
            status_code=422,
            content={"detail": [
                {"type": err.get("type", ""), "loc": list(err.get("loc", ())),
                 "msg": err.get("msg", "")}
                for err in exc.errors()
            ]},
        )

    # Registration order IS the OpenAPI path order — the schema is the committed
    # contract (scripts/gen-types.sh), so keep this order stable.
    app.include_router(routes_meta.router)
    app.include_router(routes_blueprints.router)
    app.include_router(routes_reports.router)
    app.include_router(routes_runs.router)
    app.include_router(routes_providers.router)   # LAST — order is the OpenAPI path order

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
