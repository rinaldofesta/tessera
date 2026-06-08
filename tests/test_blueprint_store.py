"""JSON-on-disk blueprint store: round-trip, seeding, CRUD, traversal safety."""

import pytest

from tessera.api import blueprint_store as bs
from tessera.examples import get_blueprint


def test_round_trip_preserves_blueprint(tmp_path):
    bp = get_blueprint("toy")
    bs.save_blueprint(tmp_path, "mine", bp)
    loaded = bs.get_blueprint(tmp_path, "mine")
    assert loaded is not None
    assert loaded.model_dump(by_alias=True) == bp.model_dump(by_alias=True)


def test_list_seeds_builtin_orgs(tmp_path):
    rows = bs.list_blueprints(tmp_path)
    by_id = {r["id"]: r for r in rows}
    assert {"toy", "your"} <= set(by_id)
    assert by_id["toy"]["claims"] > 0 and by_id["toy"]["probes"] > 0


def test_get_missing_returns_none(tmp_path):
    assert bs.get_blueprint(tmp_path, "nope") is None


def test_delete(tmp_path):
    bs.save_blueprint(tmp_path, "x", get_blueprint("toy"))
    assert bs.delete_blueprint(tmp_path, "x") is True
    assert bs.delete_blueprint(tmp_path, "x") is False


@pytest.mark.parametrize("bad", ["../evil", "a/b", "", ".hidden", "a b"])
def test_bad_ids_rejected(tmp_path, bad):
    with pytest.raises(bs.BlueprintStoreError):
        bs.get_blueprint(tmp_path, bad)
