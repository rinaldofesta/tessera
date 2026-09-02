"""Vocabulary for the Run form: runnable orgs and published model provenance."""

from __future__ import annotations

from fastapi import APIRouter, Request

from tessera.api import blueprint_store
from tessera.api import responses as R
from tessera.catalog import published_models  # re-exported: existing importers use this path

router = APIRouter()


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
    """The published model set displayed by the Run form."""
    # TESSERA_MODELS (comma-separated inspect_ai model strings) overrides the
    # published set shown at the top of the picker. Set it in .env or the shell;
    # credentials for each provider live in .env too.
    return published_models()


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

    published = set(published_models())
    models, statuses = request.app.state.discovery_cache.get()
    return {
        "defaults": {
            "engine": "deterministic", "repeats": 3,
            "grader": None,
        },
        "models": [
            {
                "id": model.id, "label": model.label, "provider": model.provider,
                "readiness": model.readiness, "source": model.source,
                "published": model.id in published, "released": model.released,
                "retired": model.retired, "detail": model.detail,
            }
            for model in models
        ],
        "suites": [suites[name] for name in sorted(suites)],
        "sources": [
            {"source": status.source, "status": status.status, "detail": status.detail}
            for status in statuses
        ],
    }
