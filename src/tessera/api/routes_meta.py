"""Vocabulary for the Run form: runnable orgs and the canonical model list."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

from tessera.api import blueprint_store

router = APIRouter()

# The canonical model list — the ONE source the UI (React Run view) reads via
# GET /api/models, so the choices can never drift from the backend.
_MODELS = [
    "anthropic/claude-sonnet-4-6",
    "openai/gpt-4o",
    "anthropic/claude-opus-4-8",
    "anthropic/claude-haiku-4-5",
    "openai/gpt-4o-mini",
    "ollama/qwen3.5:latest",
]


@router.get("/api/orgs", response_model=list[str])
def list_orgs(request: Request):
    """Runnable orgs = built-in ORGS builders + saved blueprints from the store, so a
    dataset authored on the Datasets page is immediately runnable here. Raises (500)
    if a custom org module fails to import — surfaced by the frontend as a warning."""
    from tessera.orgs import org_names
    names = set(org_names())
    try:
        names |= {b["id"] for b in
                  blueprint_store.list_blueprints(request.app.state.blueprint_dir)}
    except Exception:  # noqa: BLE001 — a broken store shouldn't hide the built-ins
        pass
    return sorted(names)


@router.get("/api/models", response_model=list[str])
def list_models():
    """The canonical model choices for the Run form (model under test + grader)."""
    # TESSERA_MODELS (comma-separated inspect_ai model strings) replaces the defaults —
    # set it in .env or the shell; credentials for each provider live in .env too.
    env = os.environ.get("TESSERA_MODELS", "")
    models = [m.strip() for m in env.split(",") if m.strip()]
    return models or _MODELS
