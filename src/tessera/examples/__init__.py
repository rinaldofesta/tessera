"""Registry of named example organizations (blueprints).

Built-in blueprints are registered here. The task and API also resolve saved suites.
"""

from __future__ import annotations

from tessera.examples.meridian_org import build_meridian_blueprint
from tessera.examples.toy_org import build_toy_blueprint

# name -> zero-arg builder. The key is what you pass as `org` or select in the UI.
ORGS = {
    "toy": build_toy_blueprint,
    "meridian": build_meridian_blueprint,
}
