"""Registry of named example organizations (blueprints).

Add your own org by writing a `build_*` function (see `your_org.py`) and registering
it in `ORGS`. The task and the API select an org by name via `get_blueprint`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from tessera.examples.meridian_org import build_meridian_blueprint
from tessera.examples.toy_org import build_toy_blueprint
from tessera.examples.your_org import build_your_blueprint
from tessera.models import Blueprint

# org/blueprint name must be a safe identifier — `name` is user-controlled (RunRequest.org
# flows here via the eval task), so this guards the JSON-store lookup against path traversal.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

# name -> zero-arg builder. The key is what you pass as `org` (CLI -T org=…,
# TESSERA_ORG=…, or the Run page picker).
ORGS = {
    "toy": build_toy_blueprint,
    "your": build_your_blueprint,
    "meridian": build_meridian_blueprint,
}


def _store_dir() -> Path:
    return Path(os.environ.get("TESSERA_BLUEPRINT_DIR", "blueprints"))


def org_names() -> list[str]:
    return sorted(ORGS)


def get_blueprint(name: str) -> Blueprint:
    """Resolve an org name to a Blueprint: a built-in ORGS builder first, else a saved
    JSON blueprint from the store (so datasets authored in the UI are runnable)."""
    builder = ORGS.get(name)
    if builder is not None:
        return builder()
    if not _SAFE_NAME.match(name or ""):
        raise ValueError(f"invalid org name {name!r}")
    base = _store_dir().resolve()
    path = (base / f"{name}.json").resolve()
    if base not in path.parents:                     # defense in depth: stay inside the store
        raise ValueError(f"invalid org name {name!r}")
    if path.exists():
        return Blueprint.model_validate_json(path.read_text())
    raise ValueError(f"unknown org {name!r}; choose from {org_names()} or a saved blueprint")
