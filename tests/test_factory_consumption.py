# tests/test_factory_consumption.py
import pytest

from tessera.factory.generate import generate_variant
from tessera.orgs import get_blueprint


def test_default_seed_is_unchanged_meridian():
    from tessera.examples.meridian_org import build_meridian_blueprint
    assert get_blueprint("meridian") == build_meridian_blueprint()


def test_meridian_seed_routes_to_factory():
    assert get_blueprint("meridian", seed=7) == generate_variant(7)


def test_nonzero_seed_on_other_org_raises():
    with pytest.raises(ValueError):
        get_blueprint("toy", seed=3)


def test_seed_zero_preserves_store_fallback_path():
    # a non-meridian builtin still resolves at seed 0 (default behavior preserved)
    assert get_blueprint("toy", seed=0).probes


def test_task_accepts_seed():
    # build the task object with a seed; offline, no model call
    from tessera.evals.task import tessera_probes
    t = tessera_probes(org="meridian", k=1, seed=5)
    assert t.dataset is not None
