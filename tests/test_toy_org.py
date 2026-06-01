from tessera.examples.toy_org import build_toy_blueprint
from tessera.models import Blueprint


def test_toy_blueprint_is_valid_and_has_three_probes():
    bp = build_toy_blueprint()
    assert isinstance(bp, Blueprint)
    kinds = {p.conflict_type.value for p in bp.probes}
    assert kinds == {"none", "resolvable", "void"}


def test_toy_resolvable_probe_requires_both_sources():
    bp = build_toy_blueprint()
    conflict = next(p for p in bp.probes if p.conflict_type.value == "resolvable")
    assert set(conflict.expected_sources) == {"acme.renewal.crm", "acme.renewal.note"}
