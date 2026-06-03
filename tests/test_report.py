import pytest

from tessera.report.models import (
    AxesSummary, CategoryReliability, ProbeEpoch, ProbeReliability, ReportError, RunHeader,
)


def test_probe_epoch_is_frozen_and_holds_fields():
    pe = ProbeEpoch(probe_id="p", epoch=1, conflict_type="none", expected_behavior="answer",
                    passed=True, accuracy_ok=True, provenance_ok=True, refusal_ok=True,
                    consulted=("crm",), expected_sources=("crm",), question="q",
                    answer="a", expected_answer="x")
    assert pe.probe_id == "p" and pe.consulted == ("crm",)
    with pytest.raises(Exception):
        pe.passed = False  # frozen dataclass


def test_report_error_is_exception():
    assert issubclass(ReportError, Exception)


from tessera.report.aggregate import reduce_by_probe


def _ep(probe_id, epoch, passed, *, ct="resolvable", beh="answer", accuracy_ok=None,
        provenance_ok=True, refusal_ok=True, consulted=(), expected_sources=(),
        question="q", answer="a", expected_answer="x"):
    """Build a ProbeEpoch with sensible defaults; accuracy_ok defaults to `passed`."""
    return ProbeEpoch(
        probe_id=probe_id, epoch=epoch, conflict_type=ct, expected_behavior=beh,
        passed=passed, accuracy_ok=(passed if accuracy_ok is None else accuracy_ok),
        provenance_ok=provenance_ok, refusal_ok=refusal_ok,
        consulted=tuple(consulted), expected_sources=tuple(expected_sources),
        question=question, answer=answer, expected_answer=expected_answer)


def test_reduce_by_probe_strict_cliff_two_of_three():
    recs = [_ep("p", 1, True), _ep("p", 2, False), _ep("p", 3, True)]
    [pr] = reduce_by_probe(recs)
    assert pr.epochs_total == 3 and pr.epochs_passed == 2
    assert pr.pass_k is False
    assert abs(pr.mean_pass - 2 / 3) < 1e-9
    assert len(pr.failures) == 1 and pr.failures[0].epoch == 2


def test_reduce_by_probe_all_pass_has_no_failures():
    recs = [_ep("p", 1, True), _ep("p", 2, True)]
    [pr] = reduce_by_probe(recs)
    assert pr.pass_k is True and pr.failures == () and pr.mean_pass == 1.0
