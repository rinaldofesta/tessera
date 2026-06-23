"""Executable anchors for the det-5 scorer candidate (docs/report.md §3.3/§6, STATE.md).

Each test asserts the behavior det-5 SHOULD have and that det-4 does NOT yet have, pinned
with xfail(strict=True): while det-4 is in force the case fails (xfail passes); the moment
det-5 lands and the case starts passing, strict mode turns the XPASS into a test failure —
forcing whoever ships det-5 to revisit these anchors and the limitation prose they encode
(evals/scoring.py "Known limitations" block; report.md §3.3 fallback strictness).

These are the three failure modes named in the det-4 limitations as the det-5 target. The
committed-line "X, not Y" / trailing-parenthetical cases are NOT here: review A1 fixed those
for the committed path via first-mention-wins over the probe's distractors (so they pass
under det-4 whenever the leading value is a registered distractor). The fallback negation
below has no ANSWER line, so it remains a genuine det-5 target.
"""

import pytest

from tessera.evals.scoring import grade_probe


@pytest.mark.xfail(strict=True, reason="det-5 target: match paraphrased dates")
def test_det5_should_match_a_paraphrased_date():
    # det-4 matches the materialized wording only; '1 March 2026' is the same date as the
    # ISO expected answer but is not matched. (No comma — isolate paraphrase, not A1's split.)
    g = grade_probe(expected_behavior="answer", expected_answer="2026-03-01",
                    expected_sources=[], consulted=set(),
                    completion="ANSWER: 1 March 2026")
    assert g["accuracy_ok"] is True


@pytest.mark.xfail(strict=True, reason="det-5 target: match paraphrased amounts")
def test_det5_should_match_a_paraphrased_amount():
    # '$1.5 million' is '$1.5M' spelled out — substantively correct, format-noncompliant.
    g = grade_probe(expected_behavior="answer", expected_answer="$1.5M",
                    expected_sources=[], consulted=set(),
                    completion="ANSWER: $1.5 million")
    assert g["accuracy_ok"] is True


@pytest.mark.xfail(strict=True, reason="det-5 target: fallback last-mention-wins mis-scores negations")
def test_det5_fallback_should_not_credit_a_negated_value():
    # no ANSWER line -> the fallback path. '7 hours, not 4 hours' asserts 7, but
    # last-mention-wins credits the trailing '4 hours' as the answer. det-5 should not.
    g = grade_probe(expected_behavior="answer", expected_answer="4 hours",
                    expected_sources=[], consulted=set(),
                    completion="The SLA is 7 hours, not 4 hours.",
                    distractor_values=["7 hours"])
    assert g["accuracy_ok"] is False
