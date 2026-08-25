"""The org registry: named blueprints selectable via the task / API."""

import pytest

from tessera.orgs import get_blueprint, org_names
from tessera.models import Blueprint, ConflictType


def test_registry_lists_builtins():
    names = org_names()
    assert "toy" in names and "your" in names


def test_get_blueprint_returns_valid_blueprints():
    for name in ("toy", "your"):
        bp = get_blueprint(name)
        assert isinstance(bp, Blueprint) and bp.claims and bp.probes


def test_your_org_template_covers_every_conflict_type():
    # The scaffold must demonstrate all four behaviors so a user has one of each to copy.
    bp = get_blueprint("your")
    assert {p.conflict_type for p in bp.probes} == set(ConflictType)


def test_unknown_org_raises():
    with pytest.raises(ValueError):
        get_blueprint("does-not-exist")


@pytest.mark.parametrize("evil", ["../secret", "../../etc/passwd", "a/b", "", ".hidden", "x/../y"])
def test_get_blueprint_rejects_path_traversal(evil, monkeypatch, tmp_path):
    # `name` reaches here from RunRequest.org (user-controlled) — must not escape the store.
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        get_blueprint(evil)


def test_get_blueprint_falls_back_to_saved_json(tmp_path, monkeypatch):
    # a dataset authored in the UI (saved to the JSON store) is runnable by name
    from tessera.api import blueprint_store as bs
    bs.save_blueprint(tmp_path, "custom_ds", get_blueprint("toy"))
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))
    bp = get_blueprint("custom_ds")
    assert bp.claims and bp.probes


def test_get_blueprint_prefers_edited_builtin_at_seed_zero(tmp_path, monkeypatch):
    """A builtin materialized by the UI becomes its runnable seed-zero source of truth."""
    from tessera.api import blueprint_store as bs

    original = get_blueprint("toy")
    edited = Blueprint(
        claims=original.claims[:-2],
        probes=[*original.probes[:2], original.probes[-1]],
    )
    bs.save_blueprint(tmp_path, "toy", edited)
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    assert get_blueprint("toy") == edited
