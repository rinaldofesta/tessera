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


from tessera.report.aggregate import aggregate_by, overall_mean_rate, overall_pass_k_rate


def _pr(probe_id, ct, pass_k, mean, *, beh="answer"):
    """Build a ProbeReliability directly (epochs derived from mean over 3)."""
    return ProbeReliability(probe_id=probe_id, conflict_type=ct, expected_behavior=beh,
                            epochs_total=3, epochs_passed=round(mean * 3), pass_k=pass_k,
                            mean_pass=mean, failures=())


def test_aggregate_by_conflict_type_is_two_level():
    probes = [_pr("a", "resolvable", True, 1.0), _pr("b", "resolvable", False, 2 / 3)]
    [cat] = aggregate_by(probes)
    assert cat.key == "resolvable" and cat.n_probes == 2
    assert cat.pass_k_rate == 0.5                              # mean of the binary cliffs
    assert abs(cat.mean_rate - (1.0 + 2 / 3) / 2) < 1e-9       # mean of the per-probe means


def test_aggregate_by_accepts_a_custom_key_seam():
    probes = [_pr("a", "none", True, 1.0), _pr("b", "void", True, 1.0)]
    cats = aggregate_by(probes, key=lambda p: "all")
    assert len(cats) == 1 and cats[0].key == "all" and cats[0].n_probes == 2


def test_overall_rates_strict_and_mean():
    probes = [_pr("a", "none", True, 1.0), _pr("b", "resolvable", False, 2 / 3)]
    assert overall_pass_k_rate(probes) == 0.5
    assert abs(overall_mean_rate(probes) - (1.0 + 2 / 3) / 2) < 1e-9
    assert overall_pass_k_rate([]) == 0.0 and overall_mean_rate([]) == 0.0


from tessera.report.aggregate import summarize_axes


def test_summarize_axes_uses_axis_specific_denominators():
    recs = [
        _ep("a1", 1, True, ct="none", beh="answer"),     # answer: accuracy_ok True
        _ep("a1", 2, False, ct="none", beh="answer"),    # answer: accuracy_ok False
        _ep("r1", 1, True, ct="void", beh="refuse"),     # refuse: refusal_ok True
    ]
    ax = summarize_axes(recs)
    assert ax.n_answer_epochs == 2 and ax.n_refuse_epochs == 1 and ax.n_total_epochs == 3
    assert ax.accuracy_rate == 0.5      # 1 of 2 answer-epochs
    assert ax.refusal_rate == 1.0       # 1 of 1 refuse-epoch
    assert ax.provenance_rate == 1.0    # 3 of 3 (default provenance_ok=True)


def test_summarize_axes_none_when_an_axis_has_no_epochs():
    ax = summarize_axes([_ep("a1", 1, True, beh="answer")])
    assert ax.refusal_rate is None      # no refuse-probe-epochs -> n/a, never a fake 0%
    assert ax.accuracy_rate == 1.0


from tessera.report.render import bar


def test_bar_full_empty_and_rounded_partial():
    assert bar(0.0) == "░░░░░░░░░░"
    assert bar(1.0) == "██████████"
    assert bar(0.67) == "███████░░░"   # round(6.7) == 7 filled
