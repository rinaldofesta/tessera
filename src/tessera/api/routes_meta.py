"""Vocabulary for the Run form: runnable orgs and the canonical model list."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

from tessera.api import blueprint_store
from tessera.api import responses as R

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

_CREDENTIAL_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "xai": "XAI_API_KEY",
    "grok": "XAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def _resolved_models() -> list[str]:
    """Resolve the canonical model list shared by /api/models and the launcher setup."""
    env = os.environ.get("TESSERA_MODELS", "")
    models = [model.strip() for model in env.split(",") if model.strip()]
    return models or _MODELS


def _model_details(model_id: str) -> dict[str, str]:
    provider, separator, label = model_id.partition("/")
    if not separator:
        return {"id": model_id, "label": model_id, "provider": "unknown", "readiness": "unknown"}
    if provider == "ollama":
        readiness = "ready"
    elif credential_env := _CREDENTIAL_ENV.get(provider):
        readiness = "ready" if os.environ.get(credential_env) else "missing_credentials"
    else:
        readiness = "unknown"
    return {"id": model_id, "label": label, "provider": provider, "readiness": readiness}


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
    return _resolved_models()


@router.get("/api/eval-setup", response_model=R.EvalSetup)
def eval_setup(request: Request):
    """Return the typed, credential-safe vocabulary and defaults for the eval launcher."""
    from tessera.orgs import get_blueprint, org_names

    # `kind` encodes origin only; it must not flip when seed_from_orgs materializes a
    # builtin into the store. Everything is editable in this product (builtins are
    # seeded precisely so the Datasets page can edit them). Store counts win over the
    # org builder's: the store copy is the runnable, possibly-edited one.
    builtins = set(org_names())
    suites: dict[str, dict] = {}
    for name in builtins:
        try:
            blueprint = get_blueprint(name)
        except Exception:  # noqa: BLE001 — a broken org builder should not break launcher setup
            continue
        suites[name] = {
            "id": name,
            "kind": "builtin",
            "editable": True,
            "claims": len(blueprint.claims),
            "questions": len(blueprint.probes),
        }
    try:
        stored = blueprint_store.list_blueprints(request.app.state.blueprint_dir, seed=False)
    except Exception:  # noqa: BLE001 — preserve built-in suite availability if the store is unavailable
        stored = []
    for blueprint in stored:
        suites[blueprint["id"]] = {
            "id": blueprint["id"],
            "kind": "builtin" if blueprint["id"] in builtins else "custom",
            "editable": True,
            "claims": blueprint["claims"],
            "questions": blueprint["probes"],
        }

    models = _resolved_models()
    return {
        "defaults": {"engine": "deterministic", "repeats": 3, "model": models[0], "grader": None},
        "models": [_model_details(model_id) for model_id in models],
        "suites": [suites[name] for name in sorted(suites)],
    }
