# tests/test_factory_validate.py
import pytest
from tessera.factory.validate import assert_variant_invariants, VariantInvariantError
from tessera.examples.meridian_org import build_meridian_blueprint
from tessera.models import Blueprint


def test_meridian_passes_all_gates():
    assert_variant_invariants(build_meridian_blueprint())   # canonical must satisfy them


def test_tampered_unresolvable_fails():
    bp = build_meridian_blueprint()
    claims = {c.claim_id: c for c in bp.claims}
    # break a tie: make the two arcadia.value claims share a value -> not a real disagreement
    p = next(p for p in bp.probes if p.probe_id == "q_arcadia_value")
    a, b = (claims[r] for r in p.references)
    tampered = [c.model_copy(update={"value": a.value}) if c.claim_id == b.claim_id else c
                for c in bp.claims]
    with pytest.raises(VariantInvariantError):
        assert_variant_invariants(Blueprint(claims=tampered, probes=bp.probes))
