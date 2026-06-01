from tessera.examples.toy_org import build_toy_blueprint
from tessera.models import Blueprint


def test_toy_blueprint_is_valid_and_covers_four_scenarios():
    bp = build_toy_blueprint()
    assert isinstance(bp, Blueprint)
    assert len(bp.probes) == 4
    kinds = {p.conflict_type.value for p in bp.probes}
    assert kinds == {"none", "resolvable", "unresolvable", "void"}


def test_toy_resolvable_probe_requires_both_sources():
    bp = build_toy_blueprint()
    conflict = next(p for p in bp.probes if p.conflict_type.value == "resolvable")
    assert set(conflict.expected_sources) == {"acme.renewal.crm", "acme.renewal.note"}


def test_toy_unresolvable_probe_is_neutralized_and_requires_both_sources():
    bp = build_toy_blueprint()
    probe = next(p for p in bp.probes if p.conflict_type.value == "unresolvable")
    assert probe.expected_behavior.value == "refuse"
    assert probe.resolution_rule is None
    assert set(probe.expected_sources) == {"globex.contract.crm", "globex.contract.note"}

    claims = {c.claim_id: c for c in bp.claims}
    crm, note = claims["globex.contract.crm"], claims["globex.contract.note"]
    assert crm.subject == note.subject == "Globex Inc"
    assert crm.predicate == note.predicate == "contract_value"
    assert crm.silo != note.silo  # the conflict is cross-silo
    assert crm.asserted_at == note.asserted_at  # recency rule neutralized
    assert crm.authority == note.authority  # authority rule neutralized
    assert crm.value != note.value  # genuinely conflicting
