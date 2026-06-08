"""Registry of named example organizations (blueprints).

Add your own org by writing a `build_*` function (see `your_org.py`) and registering
it in `ORGS`. The task and the API select an org by name via `get_blueprint`.
"""

from __future__ import annotations

import os
from pathlib import Path

from tessera.examples.toy_org import build_toy_blueprint
from tessera.examples.your_org import build_your_blueprint
from tessera.models import Blueprint

# name -> zero-arg builder. The key is what you pass as `org` (CLI -T org=…,
# TESSERA_ORG=…, or the Run page picker).
ORGS = {
    "toy": build_toy_blueprint,
    "your": build_your_blueprint,
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
    path = _store_dir() / f"{name}.json"
    if path.exists():
        return Blueprint.model_validate_json(path.read_text())
    raise ValueError(f"unknown org {name!r}; choose from {org_names()} or a saved blueprint")
