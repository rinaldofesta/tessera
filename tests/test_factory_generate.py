# tests/test_factory_generate.py
import pytest
from tessera.factory.generate import generate_variant, CANONICAL_SEED
from tessera.factory.validate import assert_variant_invariants
from tessera.examples.meridian_org import build_meridian_blueprint


def test_canonical_seed_reproduces_meridian():
    assert generate_variant(CANONICAL_SEED) == build_meridian_blueprint()


def test_seeds_are_validated():
    for bad in (-1, 1.5, "3", True):
        with pytest.raises(ValueError):
            generate_variant(bad)


def test_generated_variant_is_exactly_deterministic():
    assert generate_variant(7) == generate_variant(7)


def test_every_seed_satisfies_the_gates():
    for seed in range(1, 51):
        assert_variant_invariants(generate_variant(seed))   # also runs inside generate_variant


def test_filler_is_present():
    bp = generate_variant(3)
    assert any(c.predicate == "industry" for c in bp.claims)
