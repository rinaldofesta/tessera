"""Key-free tests for report.stats — the exact-McNemar machinery behind the scaffold
study's published p-values (docs/scaffold.md, docs/report.md §6, ADR-0009). The values
below were recomputed from the raw paired logs on 2026-07-01; if one of these moves,
a published significance claim moves with it."""

import pytest

from tessera.report.stats import exact_mcnemar_p, format_p, mcnemar_counts


def test_exact_p_reproduces_the_published_scaffold_study_values():
    # b = discordants where R1 hurt, c = where R1 helped (order must not matter).
    published = [
        (1, 18, 7.62939453125e-05),      # sonnet, refusal subset -> "p = 0.0001"
        (2, 24, 1.049041748046875e-05),  # sonnet, overall        -> "p < 0.0001"
        (1, 6, 0.125),                   # sonnet, answerable subset
        (0, 9, 0.00390625),              # gpt-4o, refusal subset -> "p = 0.004"
        (1, 10, 0.01171875),             # gpt-4o, overall        -> "p = 0.012"
        (1, 9, 0.021484375),             # haiku, refusal subset  -> "p = 0.021"
        (10, 4, 0.1795654296875),        # haiku, resolvable column
        (14, 8, 0.28627872467041016),    # haiku, answerable subset -> "p = 0.29"
        (15, 17, 0.8600499),             # haiku, overall         -> "p = 0.86"
        (6, 2, 0.2890625),               # gpt-4o-mini, overall   -> "p = 0.29"
    ]
    for b, c, expected in published:
        assert exact_mcnemar_p(b, c) == pytest.approx(expected, rel=1e-6)


def test_exact_p_is_symmetric_in_its_arguments():
    assert exact_mcnemar_p(3, 7) == exact_mcnemar_p(7, 3)


def test_exact_p_without_discordants_is_one():
    assert exact_mcnemar_p(0, 0) == 1.0


def test_exact_p_is_clamped_at_one_when_arms_tie():
    # Doubling the tail at b == c overshoots 1; the convention clamps.
    assert exact_mcnemar_p(5, 5) == 1.0


def test_format_p_floors_below_the_reporting_precision():
    # {:.4f} would render sonnet's overall p as the impossible "0.0000".
    assert format_p(1.05e-05) == "< 0.0001"
    assert format_p(0.021484375) == "0.0215"
    assert format_p(1.0) == "1.0000"


def test_mcnemar_counts_pairs_by_key_and_reports_dropped():
    # Probes present in only one arm must be surfaced, not silently shrunk away:
    # a dropped pair changes n and therefore the p-value.
    b0 = {"a": True, "b": False, "c": True}
    r1 = {"a": False, "b": True, "d": True}
    b, c, dropped = mcnemar_counts(b0, r1)
    assert (b, c) == (1, 1)
    assert dropped == ("c", "d")


def test_mcnemar_counts_concordant_pairs_do_not_count():
    b0 = {"a": True, "b": False}
    r1 = {"a": True, "b": False}
    assert mcnemar_counts(b0, r1) == (0, 0, ())
