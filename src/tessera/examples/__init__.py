"""Registry of named example organizations (blueprints).

Add your own org by writing a `build_*` function (see `your_org.py`) and registering
it in `ORGS`. The task and the API select an org by name via `get_blueprint`.
"""

from __future__ import annotations

from tessera.examples.toy_org import build_toy_blueprint
from tessera.examples.your_org import build_your_blueprint
from tessera.models import Blueprint

# name -> zero-arg builder. The key is what you pass as `org` (CLI -T org=…,
# TESSERA_ORG=…, or the Run page picker).
ORGS = {
    "toy": build_toy_blueprint,
    "your": build_your_blueprint,
}


def org_names() -> list[str]:
    return sorted(ORGS)


def get_blueprint(name: str) -> Blueprint:
    builder = ORGS.get(name)
    if builder is None:
        raise ValueError(f"unknown org {name!r}; choose from {org_names()}")
    return builder()
