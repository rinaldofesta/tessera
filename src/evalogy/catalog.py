"""Canonical Evalogy vocabulary shared by the CLI, API, and web Run form."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import ValidationError

from evalogy import paths
from evalogy.api.providers import is_configured, provider_for_model
from evalogy.contract import Catalog, CatalogSuite, Defaults
from evalogy.errors import SpecError
from evalogy.models import Blueprint
from evalogy.providers import connection_state

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
    "anthropic/claude-fable-5",
    "anthropic/claude-sonnet-5",
]

_LOG = logging.getLogger(__name__)


def published_models() -> list[str]:
    """The published model set: $EVALOGY_MODELS (comma-separated) or the built-in list."""
    env = os.environ.get("EVALOGY_MODELS", "")
    models = [model.strip() for model in env.split(",") if model.strip()]
    return models or _PUBLISHED_MODELS



def _suite_row(name: str, blueprint: Blueprint, builtin: dict | None = None) -> dict:
    return {
        "name": name,
        "label": builtin["label"] if builtin else name,
        "org": builtin["org"] if builtin else name,
        "kind": "builtin" if builtin else "user",
        "questions": len(blueprint.probes),
        "claims": len(blueprint.claims),
        "editable": not builtin,
    }


def _builtin_suites(suites_dir: Path) -> list[dict]:
    # store_dir=suites_dir: get_blueprint() otherwise resolves its OWN store via
    # EVALOGY_BLUEPRINT_DIR/EVALOGY_HOME, ignoring whatever directory the caller (e.g.
    # app.state.blueprint_dir) actually injected — the two can silently disagree.
    from evalogy.examples import ORGS
    from evalogy.orgs import get_blueprint

    suites = []
    for name, metadata in BUILTIN_SUITES.items():
        org = metadata["org"]
        try:
            blueprint = get_blueprint(org, store_dir=suites_dir)
        except Exception:  # noqa: BLE001 — a corrupt store override must not hide the catalog
            _LOG.warning(
                "store override for org '%s' is unparseable; using the packaged blueprint", org)
            blueprint = ORGS[org]()
        suites.append(_suite_row(name, blueprint, metadata))
    return suites


def _user_suites(directory: Path) -> list[dict]:
    # blueprint_store.seed_from_orgs() materializes every builtin ORGS example into
    # this SAME directory the moment the Datasets page is
    # opened (GET /api/blueprints), so those files are not distinct user suites — they
    # are editable copies of orgs BUILTIN_SUITES already exposes. Without this filter
    # a seeded 'meridian.json' collides with the builtin 'meridian' suite name and
    # produces a duplicate, contradictory row (kind='builtin' AND kind='user' at once).
    from evalogy.examples import ORGS

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
        suites.append(_suite_row(suite_path.stem, blueprint))
    return suites


def _suite_rows(suites_dir: Path | None) -> list[dict]:
    directory = suites_dir or paths.suites_dir()
    return [*_builtin_suites(directory), *_user_suites(directory)]


def build_catalog(
    *, env: Mapping[str, str] = os.environ, suites_dir: Path | None = None,
) -> dict:
    """Build the complete credential-safe catalog without performing discovery."""
    # These imports stay local so importing evalogy.catalog never initializes inspect_ai.
    from evalogy.evals.scoring import SCORER_VERSIONS
    from evalogy.evals.task import _SCAFFOLDS

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


def resolve_suite(ref: str, *, suites_dir: Path | None = None, seed: int = 0) -> tuple[dict, list[str]]:
    from evalogy.api.blueprint_store import validation_issues
    from evalogy.orgs import get_blueprint

    diagnostics = []
    resolved = SUITE_ALIASES.get(ref, ref)
    if resolved != ref:
        diagnostics.append(f"suite '{ref}' is now called '{resolved}'")

    builtin = BUILTIN_SUITES.get(resolved)
    org = builtin["org"] if builtin else resolved
    try:
        blueprint = get_blueprint(org, store_dir=suites_dir or paths.suites_dir(),
                                  seed=seed if org == "meridian" else 0)
    except ValidationError as exc:
        issues = validation_issues(exc)
        message = "; ".join(f"{issue['location']}: {issue['message']}" for issue in issues)
        raise SpecError(f"invalid suite '{ref}': {message}") from None
    except (ValueError, OSError):
        available = ", ".join(suite["name"] for suite in _suite_rows(suites_dir))
        raise SpecError(f"unknown suite '{ref}'; available: {available}") from None
    row = _suite_row(resolved, blueprint, builtin)
    return CatalogSuite.model_validate(row).model_dump(), diagnostics
