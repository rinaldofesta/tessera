"""The org registry: named blueprints selectable via the task / API."""

import pytest

from tessera.examples import get_blueprint, org_names
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
