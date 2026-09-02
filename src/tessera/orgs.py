"""Resolve an org name (and optional factory seed) to a Blueprint.

Sits above `examples` (the authored registry) and `factory` (the seeded generator), so
imports flow one way: this module imports both; `factory` imports `examples`;
`examples` imports neither. The task and the API select an org by name here.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from tessera import paths
from tessera.examples import ORGS
from tessera.factory.generate import generate_variant
from tessera.models import Blueprint

# org/blueprint name must be a safe identifier — `name` is user-controlled (RunSpec.suite
# flows here via the eval task), so this guards the JSON-store lookup against path traversal.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _store_dir() -> Path:
    if "TESSERA_BLUEPRINT_DIR" in os.environ:
        return Path(os.environ["TESSERA_BLUEPRINT_DIR"])
    return paths.suites_dir()


def org_names() -> list[str]:
    return sorted(ORGS)


def get_blueprint(name: str, seed: int = 0, *, store_dir: Path | None = None) -> Blueprint:
    """Resolve an org name to a Blueprint: a saved JSON blueprint first, else a built-in
    ORGS builder. `seed` selects a scenario-factory variant of the meridian family
    (seed 0 = the editable/canonical org); a non-zero seed is only valid for `meridian`
    and deliberately bypasses the store. `store_dir` overrides the store location for
    callers that already resolved one (e.g. app.state.blueprint_dir) instead of
    silently falling back to the process-wide TESSERA_BLUEPRINT_DIR/TESSERA_HOME —
    the two can disagree, and this is the only lookup path that would otherwise ignore
    an explicitly injected store."""
    if seed != 0:
        if name != "meridian":
            raise ValueError(f"seed addressing is only supported for 'meridian', not {name!r}")
        return generate_variant(seed)
    if not _SAFE_NAME.match(name or ""):
        raise ValueError(f"invalid org name {name!r}")
    base = (store_dir if store_dir is not None else _store_dir()).resolve()
    path = (base / f"{name}.json").resolve()
    if base not in path.parents:                     # defense in depth: stay inside the store
        raise ValueError(f"invalid org name {name!r}")
    if path.exists():
        return Blueprint.model_validate_json(path.read_text())
    builder = ORGS.get(name)
    if builder is not None:
        return builder()
    raise ValueError(f"unknown org {name!r}; choose from {org_names()} or a saved blueprint")
