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


from tessera.report.render import render_scorecard


def _hdr(k=3, engine="llm"):
    return RunHeader(model="anthropic/claude-sonnet-4-6", engine=engine, k=k,
                     created="2026-06-03", location="./logs/x.eval",
                     grader=("openai/gpt-4o" if engine == "llm" else None))


def test_render_scorecard_overall_canonical_order_and_flaky():
    cats = [
        CategoryReliability("void", 1, 1.0, 1.0),
        CategoryReliability("none", 1, 1.0, 1.0),
        CategoryReliability("resolvable", 1, 0.0, 2 / 3),   # capable but inconsistent
    ]
    out = render_scorecard(_hdr(k=3), 0.5, 0.75, cats)
    assert "OVERALL  pass^3  50%   (mean 75%)" in out
    assert out.index("none") < out.index("resolvable") < out.index("void")  # canonical, not input order
    assert "⚠ flaky" in out                       # mean 67% > pass^k 0%
    assert "unresolvable" not in out              # categories absent from the run are skipped


def test_render_scorecard_no_flaky_when_consistent():
    out = render_scorecard(_hdr(k=3), 1.0, 1.0, [CategoryReliability("none", 1, 1.0, 1.0)])
    assert "⚠ flaky" not in out


from tessera.report.render import render_axes


def test_render_axes_table_with_na_for_missing_axis():
    ax = AxesSummary(accuracy_rate=0.75, provenance_rate=0.92, refusal_rate=None,
                     n_answer_epochs=6, n_refuse_epochs=0, n_total_epochs=12)
    out = render_axes(ax)
    assert "Accuracy" in out and "75%" in out and "answer probe-epochs (6)" in out
    assert "Provenance" in out and "92%" in out and "all probe-epochs (12)" in out
    assert "Refusal" in out and "n/a" in out and "refuse probe-epochs (0)" in out


from tessera.report.render import render_appendix


def test_render_appendix_lists_only_failures_with_missing_and_locator():
    fe = _ep("q_acme_renewal", 2, False, ct="resolvable", accuracy_ok=True,
             provenance_ok=False, consulted=("crm",),
             expected_sources=("crm", "acme.renewal.note"),
             question="When is Acme's renewal?", answer="2026-03-01 (per CRM)")
    failed = ProbeReliability("q_acme_renewal", "resolvable", "answer", 3, 2, False, 2 / 3, (fe,))
    clean = ProbeReliability("q_ok", "none", "answer", 3, 3, True, 1.0, ())
    out = render_appendix([failed, clean], _hdr(k=3))
    assert "q_acme_renewal" in out and "q_ok" not in out           # failures only
    assert "**Q:** When is Acme's renewal?" in out
    assert "missing: acme.renewal.note" in out
    assert "locate: sample `q_acme_renewal`, epoch 2" in out
    assert "(2/3 epochs)" in out


def test_render_appendix_clean_run_confirmation_line():
    clean = ProbeReliability("q_ok", "none", "answer", 3, 3, True, 1.0, ())
    out = render_appendix([clean], _hdr(k=3))
    assert "All 1 probes passed pass^3 — no diagnostics." in out
