"""Vocabulary for the Run form: runnable orgs and the canonical model list."""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Request

from tessera.api import blueprint_store
from tessera.api import responses as R
from tessera.api.discovery.merge import resolved_model_ids

router = APIRouter()


def _resolved_models() -> list[str]:
    """Resolve the canonical model list shared by /api/models and the launcher setup."""
    # Keep this legacy endpoint aligned with the benchmark/configured group. The richer
    # launcher contract reads the cached discovery snapshot below.
    return resolved_model_ids(os.environ)


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

    discovery = request.app.state.discovery_cache.snapshot()
    models = [model.as_dict() for model in discovery.models]
    return {
        "defaults": {
            "engine": "deterministic",
            "repeats": 3,
            "model": models[0]["id"],
            "grader": None,
        },
        "models": models,
        "sources": [source.as_dict() for source in discovery.sources],
        "suites": [suites[name] for name in sorted(suites)],
    }


@router.post("/api/model-discovery/rescan", response_model=R.ModelDiscoveryPayload)
async def rescan_models(request: Request):
    """Force one bounded discovery refresh; normal setup reads never perform I/O."""
    cache = request.app.state.discovery_cache
    cache.invalidate()
    discovery = await asyncio.to_thread(cache.refresh)
    return discovery.as_dict()
