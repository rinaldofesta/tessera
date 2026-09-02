# tests/test_factory_properties.py
import os
import subprocess
import sys
from collections import Counter

from tessera.examples.meridian_org import build_meridian_blueprint
from tessera.factory.generate import generate_variant
from tessera.factory.schema import CANONICAL_ANSWERS


def test_distinct_seeds_yield_distinct_blueprints():
    seeds = [1, 2, 3, 5, 8, 13, 21]
    blobs = {generate_variant(s).model_dump_json() for s in seeds}
    assert len(blobs) == len(seeds)


def test_holdout_winning_answers_differ_from_canonical():
    # for answer-bearing probes that exist in a variant, the winning answer must not be the
    # published canonical answer for that probe_id
    for seed in (1, 7, 19, 33):
        bp = generate_variant(seed)
        for p in bp.probes:
            if p.expected_answer and p.probe_id in CANONICAL_ANSWERS:
                assert p.expected_answer != CANONICAL_ANSWERS[p.probe_id], (seed, p.probe_id)


def test_conflict_assignment_differs_across_seeds():
    def refuse_set(seed):
        bp = generate_variant(seed)
        return frozenset(p.probe_id for p in bp.probes
                         if p.conflict_type.value in ("unresolvable", "void"))
    assert len({refuse_set(s) for s in range(1, 30)}) > 1


def test_generated_path_matches_canonical_shape():
    # two-path parity: a generated variant has the same per-category probe counts as the
    # canonical draw, and its none chains all carry exactly one CRM + one docs claim.
    canon_counts = Counter(p.conflict_type.value for p in build_meridian_blueprint().probes)
    for seed in (1, 7, 42):
        bp = generate_variant(seed)
        assert Counter(p.conflict_type.value for p in bp.probes) == canon_counts
        claims = {c.claim_id: c for c in bp.claims}
        for p in bp.probes:
            if p.conflict_type.value == "none":
                silos = sorted(claims[r].silo for r in p.references)
                assert silos == ["crm", "docs"], (seed, p.probe_id)


def test_no_seed_in_a_wide_range_crashes_the_invariant_gates():
    # generate_variant runs assert_variant_invariants. A resolvable slot whose loser is a
    # substring of the winner ('2.9%'/'12.9%', '96'/'196') used to empty the distractor
    # set and raise VariantInvariantError on ~0.34% of seeds (218, 1742, 1771, 1846,
    # 1974, ...), silently breaking the holdout reveal guarantee — a coordinator could
    # commit to a seed that cannot be revealed. Every seed in a wide band must generate.
    for seed in range(1, 2000):
        generate_variant(seed)


def test_same_seed_reproduces_an_identical_blueprint():
    # the holdout reveal-and-reproduce guarantee rests on same-seed -> identical Blueprint
    # for EVERY seed, not just the one the cross-machine test pins. A path stable at one
    # seed but not others would slip past a single-seed assertion.
    for seed in (1, 2, 7, 19, 42, 99):
        assert (generate_variant(seed).model_dump_json()
                == generate_variant(seed).model_dump_json()), seed


def test_cross_machine_determinism_under_pythonhashseed():
    # hash randomization is per-process and must be set before interpreter start; a set/dict
    # leaking into the rng path would make the output depend on PYTHONHASHSEED. Checked over
    # several seeds, not just one.
    for seed in (1, 7, 42):
        code = ("from tessera.factory.generate import generate_variant; "
                f"print(generate_variant({seed}).model_dump_json())")
        outs = set()
        for hs in ("0", "12345"):
            result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                                    text=True, env={**os.environ, "PYTHONHASHSEED": hs})
            assert result.returncode == 0, result.stderr
            outs.add(result.stdout)
        assert len(outs) == 1, seed            # identical regardless of hash seed
