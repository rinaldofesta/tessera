"""FastAPI app: the Tessera Reliability Explorer API.

Endpoints include provider configuration, dataset authoring, folder-backed runs,
the offline catalog, and paired run comparisons.

Handlers live in focused route modules and read their injected seams via
request.app.state. Every JSON endpoint declares a response_model (see responses.py) —
the OpenAPI schema they produce is the contract web/src/api-types.gen.ts is generated
from.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from importlib import resources
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import tessera
from tessera import paths
from tessera.api import (
    routes_blueprints,
    routes_catalog,
    routes_comparisons,
    routes_providers,
    routes_runs,
)
from tessera.store import RunStore


def _resolve_env_file(env_file: Path | None) -> Path:
    """One authoritative absolute path. Resolved, never read, at construction time."""
    chosen = env_file if env_file is not None else paths.env_file()
    return Path(chosen).resolve()


async def _background_schedule(coro) -> None:
    """Production scheduler: fire-and-forget on the running loop (job stays 'running')."""
    asyncio.create_task(coro)


def _package_path(*parts: str) -> Path:
    return Path(str(resources.files("tessera.data").joinpath(*parts)))


def ui_dist() -> Path | None:
    """Return the installed UI directory, or the checkout build when developing."""
    candidates = (
        _package_path("web"),
        Path(tessera.__file__).parents[2] / "web" / "dist",
    )
    return next((candidate for candidate in candidates if (candidate / "index.html").is_file()), None)


def lesson_path() -> Path:
    """Prefer the installed lesson while retaining the source-checkout fallback."""
    packaged = _package_path("lesson.html")
    if packaged.is_file():
        return packaged
    return Path(tessera.__file__).parents[2] / "docs" / "tessera-lesson.html"


def create_app(home: Path | None = None, folder_eval_runner=None,
               schedule=_background_schedule, blueprint_dir: Path | None = None,
               env_file: Path | None = None) -> FastAPI:

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
        interrupted = app.state.runs.reconcile()
        if interrupted:
            logging.getLogger("tessera").info(
                "reconciled interrupted runs: %s", ", ".join(interrupted),
            )
        yield

    app = FastAPI(title="Tessera Reliability Explorer", lifespan=lifespan)
    app.state.runs = RunStore(home or paths.home())
    app.state.folder_eval_runner = folder_eval_runner
    app.state.schedule = schedule
    app.state.blueprint_dir = blueprint_dir or paths.suites_dir()
    app.state.env_file = _resolve_env_file(env_file)

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

    # The committed contract (scripts/gen-types.sh) is dumped with sorted keys, so
    # registration order no longer leaks into openapi.json.
    app.include_router(routes_blueprints.router)
    # Catalog precedes runs by convention; dry-run is POST while the dynamic run route is GET.
    app.include_router(routes_catalog.router)
    app.include_router(routes_runs.router)
    app.include_router(routes_providers.router)
    app.include_router(routes_comparisons.router)

    _mount_learn(app)
    _mount_spa(app)
    return app


def _mount_learn(app: FastAPI, lesson: Path | None = None) -> None:
    """Serve the plain-language guide at /learn. Excluded from the OpenAPI schema on
    purpose: it is a static page for humans, not part of the typed contract."""
    from fastapi.responses import FileResponse

    lesson = lesson or lesson_path()

    @app.get("/learn", include_in_schema=False)
    def learn():
        if not lesson.exists():
            raise HTTPException(404, "guide not found")
        return FileResponse(lesson, media_type="text/html")


def _mount_spa(app: FastAPI, dist: Path | None = None) -> None:
    """If the built React SPA exists, serve it: hashed assets at /assets and an
    index.html fallback for client-side routes. Registered AFTER the /api routes (and
    after FastAPI's /docs, /openapi.json), so they always take precedence."""
    dist = dist or ui_dist()
    if dist is None or not (dist / "index.html").is_file():
        return
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    assets = dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    # Not part of the API contract: whether a bundle is present must not change
    # openapi.json (the checkout may have web/dist built; CI's contract job does not).
    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        include_in_schema=False,
    )
    def spa(request: Request, full_path: str):
        # Never let the SPA fallback swallow unmatched API routes — keep their 404s
        # honest for every method, including routes removed from an earlier contract.
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(404, "not found")
        if request.method != "GET":
            raise HTTPException(405, "method not allowed")
        return FileResponse(dist / "index.html")


def main() -> None:
    import uvicorn

    uvicorn.run("tessera.api.app:create_app", factory=True, host="127.0.0.1",
                port=int(os.environ.get("TESSERA_API_PORT", "8000")))


if __name__ == "__main__":
    main()
