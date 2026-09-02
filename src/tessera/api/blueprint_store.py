"""JSON-on-disk store for editable blueprints (datasets).

Blueprints round-trip through Blueprint JSON (model_dump(by_alias=True) /
model_validate_json) — never Python source — so the UI can create and edit datasets.
Git-diffable files suit the code-comfortable persona. Built-in example orgs are seeded
in on first read so they show up immediately and editably.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tessera.models import Blueprint

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class BlueprintStoreError(Exception):
    """Expected, user-facing store failure (bad id, missing, conflict)."""


def _safe_path(store_dir: str | Path, blueprint_id: str) -> Path:
    """Resolve an id to a path inside store_dir; reject anything path-traversal-y."""
    if not _ID.match(blueprint_id or ""):
        raise BlueprintStoreError(
            f"invalid blueprint id {blueprint_id!r} (use letters, digits, '-' and '_')")
    base = Path(store_dir)
    candidate = (base / f"{blueprint_id}.json").resolve()
    if base.resolve() not in candidate.parents:
        raise BlueprintStoreError("blueprint id escapes the store directory")
    return candidate


def seed_from_orgs(store_dir: str | Path) -> None:
    """Materialize built-in ORGS as editable JSON (only if not already present)."""
    from tessera.examples import ORGS
    from tessera.orgs import get_blueprint
    for name in ORGS:
        path = Path(store_dir) / f"{name}.json"
        if not path.exists():
            save_blueprint(store_dir, name, get_blueprint(name))


def list_blueprints(store_dir: str | Path, *, seed: bool = True) -> list[dict]:
    if seed:
        seed_from_orgs(store_dir)
    base = Path(store_dir)
    out: list[dict] = []
    if base.exists():
        for path in sorted(base.glob("*.json")):
            try:
                bp = Blueprint.model_validate_json(path.read_text())
            except Exception:  # noqa: BLE001 — skip unreadable files, don't crash the list
                continue
            out.append({"id": path.stem, "claims": len(bp.claims), "probes": len(bp.probes)})
    return out


def get_blueprint(store_dir: str | Path, blueprint_id: str) -> Blueprint | None:
    path = _safe_path(store_dir, blueprint_id)
    if not path.exists():
        return None
    return Blueprint.model_validate_json(path.read_text())


def save_blueprint(store_dir: str | Path, blueprint_id: str, blueprint: Blueprint) -> None:
    path = _safe_path(store_dir, blueprint_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    # by_alias so Render.as_ serializes as "as" and round-trips cleanly.
    path.write_text(json.dumps(blueprint.model_dump(by_alias=True), indent=2) + "\n")


def delete_blueprint(store_dir: str | Path, blueprint_id: str) -> bool:
    path = _safe_path(store_dir, blueprint_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def exists(store_dir: str | Path, blueprint_id: str) -> bool:
    return _safe_path(store_dir, blueprint_id).exists()


def validate_and_build(data: dict) -> tuple[Blueprint | None, list[dict[str, str]]]:
    """(blueprint, errors): validate the Pydantic shape and compile it without writing
    artifacts, keeping the built model for callers that need it — so a caller that wants
    both the validated model and the errors doesn't have to re-parse the same payload."""
    from pydantic import ValidationError

    from tessera.compiler import build_artifacts

    try:
        blueprint = Blueprint.model_validate(data)
    except ValidationError as exc:
        return None, [
            {
                "location": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
    try:
        build_artifacts(blueprint)
    except ValueError as exc:
        return None, [{"location": "compile", "message": str(exc)}]
    return blueprint, []


def validate_blueprint(data: dict) -> list[dict[str, str]]:
    """Validate the Pydantic shape and compile it without writing artifacts."""
    return validate_and_build(data)[1]
