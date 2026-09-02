# tests/test_factory_export.py
import json

from tessera.factory.export import export_variant
from tessera.factory.generate import generate_variant
from tessera.factory.schema import FACTORY_VERSION
from tessera.models import Blueprint


def test_export_writes_blueprint_and_answers(tmp_path):
    bp_path, ans_path = export_variant(7, tmp_path)
    # blueprint reloads via the model
    bp = Blueprint.model_validate_json(bp_path.read_text())
    assert bp == generate_variant(7)
    # answer key is self-describing and matches the probes
    ans = json.loads(ans_path.read_text())
    assert ans["seed"] == 7 and ans["factory_version"] == FACTORY_VERSION
    for p in bp.probes:
        rec = ans["answers"][p.probe_id]
        assert rec["expected_behavior"] == p.expected_behavior.value
        assert rec["expected_answer"] == p.expected_answer
        assert rec["expected_sources"] == list(p.expected_sources)


def test_filenames_follow_convention(tmp_path):
    bp_path, ans_path = export_variant(7, tmp_path)
    assert bp_path.name == "meridian-seed7.blueprint.json"
    assert ans_path.name == "meridian-seed7.answers.json"
