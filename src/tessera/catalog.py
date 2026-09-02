"""Canonical Tessera vocabulary shared by the CLI, API, and web launcher."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path

from tessera import paths
from tessera.api.providers import is_configured, provider_for_model
from tessera.contract import Catalog, CatalogSuite, Defaults
from tessera.errors import SpecError
from tessera.models import Blueprint
from tessera.providers import connection_state

DEFAULTS = Defaults()

BUILTIN_SUITES = {
    "starter": {"org": "toy", "label": "Starter — 4 questions"},
    "meridian": {"org": "meridian", "label": "Meridian — 22 questions"},
}
SUITE_ALIASES = {"toy": "starter"}

_PUBLISHED_MODELS = [
    "anthropic/claude-sonnet-4-6",
    "openai/gpt-4o",
    "anthropic/claude-opus-4-8",
    "anthropic/claude-haiku-4-5",
    "openai/gpt-4o-mini",
    "ollama/qwen3.5:latest",
    "anthropic/claude-fable-5",
    "anthropic/claude-sonnet-5",
]

_LOG = logging.getLogger(__name__)


def published_models() -> list[str]:
    """The published model set: $TESSERA_MODELS (comma-separated) or the built-in list."""
    env = os.environ.get("TESSERA_MODELS", "")
    models = [model.strip() for model in env.split(",") if model.strip()]
    return models or _PUBLISHED_MODELS



def _builtin_suites(suites_dir: Path) -> list[dict]:
    # store_dir=suites_dir: get_blueprint() otherwise resolves its OWN store via
    # TESSERA_BLUEPRINT_DIR/TESSERA_HOME, ignoring whatever directory the caller (e.g.
    # app.state.blueprint_dir) actually injected — the two can silently disagree.
    from tessera.examples import ORGS
    from tessera.orgs import get_blueprint

    suites = []
    for name, metadata in BUILTIN_SUITES.items():
        org = metadata["org"]
        try:
            blueprint = get_blueprint(org, store_dir=suites_dir)
        except Exception:  # noqa: BLE001 — a corrupt store override must not hide the catalog
            _LOG.warning(
                "store override for org '%s' is unparseable; using the packaged blueprint", org)
            blueprint = ORGS[org]()
        suites.append({
            "name": name,
            "label": metadata["label"],
            "org": org,
            "kind": "builtin",
            "questions": len(blueprint.probes),
            "claims": len(blueprint.claims),
            "editable": False,
        })
    return suites


def _user_suites(directory: Path) -> list[dict]:
    # blueprint_store.seed_from_orgs() materializes every builtin ORGS example into
    # this SAME directory the moment the Datasets page is
    # opened (GET /api/blueprints), so those files are not distinct user suites — they
    # are editable copies of orgs BUILTIN_SUITES already exposes. Without this filter
    # a seeded 'meridian.json' collides with the builtin 'meridian' suite name and
    # produces a duplicate, contradictory row (kind='builtin' AND kind='user' at once).
    from tessera.examples import ORGS

    suites = []
    if not directory.exists():
        return suites
    for suite_path in sorted(directory.glob("*.json")):
        if suite_path.stem in ORGS:
            continue
        try:
            blueprint = Blueprint.model_validate_json(suite_path.read_text())
        except Exception:  # noqa: BLE001 — one bad user file must not hide the catalog
            _LOG.warning("skipping unparseable user suite '%s'", suite_path.stem)
            continue
        suites.append({
            "name": suite_path.stem,
            "label": suite_path.stem,
            "org": suite_path.stem,
            "kind": "user",
            "questions": len(blueprint.probes),
            "claims": len(blueprint.claims),
            "editable": True,
        })
    return suites


def _suite_rows(suites_dir: Path | None) -> list[dict]:
    directory = suites_dir or paths.suites_dir()
    return [*_builtin_suites(directory), *_user_suites(directory)]


def build_catalog(
    *, env: Mapping[str, str] = os.environ, suites_dir: Path | None = None,
) -> dict:
    """Build the complete credential-safe catalog without performing discovery."""
    # These imports stay local so importing tessera.catalog never initializes inspect_ai.
    from tessera.evals.scoring import SCORER_VERSIONS
    from tessera.evals.task import _SCAFFOLDS

    models = []
    for model_id in published_models():
        spec = provider_for_model(model_id)
        models.append({
            "id": model_id,
            "label": model_id,
            "provider": spec.id if spec else "unknown",
            "connected": bool(spec and is_configured(spec, env)),
        })

    scorers = [
        {"engine": engine, "version": version}
        for engine, version in SCORER_VERSIONS.items()
    ]
    return Catalog(
        suites=_suite_rows(suites_dir),
        models=models,
        providers=connection_state(env),
        scorers=scorers,
        scaffolds=sorted(_SCAFFOLDS),
        defaults=DEFAULTS,
    ).model_dump()


def suite_name_for_org(org: str | None) -> str:
    """The user-facing suite name for a protocol org id found in a log header. Logs
    written before `org` was recorded ran the default org, which is the default suite."""
    if org is None:
        return DEFAULTS.suite
    for name, metadata in BUILTIN_SUITES.items():
        if metadata["org"] == org:
            return name
    return org


def resolve_suite(ref: str, *, suites_dir: Path | None = None) -> tuple[dict, list[str]]:
    diagnostics = []
    resolved = SUITE_ALIASES.get(ref, ref)
    if resolved != ref:
        diagnostics.append(f"suite '{ref}' is now called '{resolved}'")

    suites = _suite_rows(suites_dir)
    for suite in suites:
        if suite["name"] == resolved:
            return CatalogSuite.model_validate(suite).model_dump(), diagnostics

    available = ", ".join(suite["name"] for suite in suites)
    raise SpecError(f"unknown suite '{ref}'; available: {available}")
