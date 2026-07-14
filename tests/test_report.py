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


from tessera.report import render_report  # re-exported from the package root


def test_render_report_assembles_all_sections_and_footer():
    hdr = _hdr(k=3, engine="llm")
    probe = ProbeReliability("q_ok", "none", "answer", 3, 3, True, 1.0, ())
    cats = [CategoryReliability("none", 1, 1.0, 1.0)]
    axes = AxesSummary(1.0, 1.0, None, 3, 0, 3)
    out = render_report(hdr, 1.0, 1.0, cats, axes, [probe])
    assert out.startswith("# Tessera Reliability Report")
    assert "**Model:** anthropic/claude-sonnet-4-6 · **Engine:** llm (grader: openai/gpt-4o)" in out
    assert "**Run:** 2026-06-03 · **Probes:** 1 × 3 epochs" in out
    assert "## Reliability — pass^3 (strict)" in out
    assert "## Operational axes (across probe-epochs)" in out
    assert "## Diagnostic appendix — failed pass^3" in out
    assert "inspect view --log-dir ./logs" in out
    assert 'read_eval_log_sample("./logs/x.eval", "<probe_id>", epoch=N)' in out


from tessera.report.log_adapter import eval_log_to_records


def _eval_log(samples, *, judge="llm", epochs=3, grader="openai/gpt-4o",
              model="anthropic/claude-sonnet-4-6", location="./logs/run.eval",
              task_args=None):
    from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSpec
    from inspect_ai.model import ModelConfig
    roles = {"grader": ModelConfig(model=grader)} if grader else {}
    spec = EvalSpec(created="2026-06-03T10:00:00+00:00", task="tessera_probes",
                    dataset=EvalDataset(), model=model, config=EvalConfig(epochs=epochs),
                    task_args=(task_args if task_args is not None else {"judge": judge}),
                    model_roles=roles)
    # A directly-constructed EvalLog has location="" by default; set it so the adapter
    # has a stable path to surface (read_eval_log fills this in on the real path).
    return EvalLog(eval=spec, samples=samples, location=location)


def _eval_sample(probe_id, epoch, *, conflict_type, expected_behavior, passed, accuracy_ok,
                 provenance_ok, refusal_ok, consulted, expected_sources, answer,
                 scorer_name="llm_reliability_scorer", question="Q?", expected_answer=None):
    from inspect_ai.log import EvalSample
    from inspect_ai.scorer import Score
    return EvalSample(
        id=probe_id, epoch=epoch, input=question, target=expected_answer or "",
        metadata={"conflict_type": conflict_type, "expected_behavior": expected_behavior,
                  "expected_answer": expected_answer, "expected_sources": list(expected_sources)},
        scores={scorer_name: Score(value=("C" if passed else "I"), answer=answer,
                metadata={"passed": passed, "accuracy_ok": accuracy_ok,
                          "provenance_ok": provenance_ok, "refusal_ok": refusal_ok,
                          "consulted": list(consulted)})})


def test_eval_log_to_records_reads_header_and_record():
    s = _eval_sample("q_globex_contract", 2, conflict_type="unresolvable",
                     expected_behavior="refuse", passed=False, accuracy_ok=False,
                     provenance_ok=True, refusal_ok=False, consulted=["globex.contract.crm"],
                     expected_sources=["globex.contract.crm", "globex.contract.note"],
                     answer="$1.2M")
    header, records = eval_log_to_records(_eval_log([s]))
    assert header.model == "anthropic/claude-sonnet-4-6"
    assert header.engine == "llm" and header.grader == "openai/gpt-4o" and header.k == 3
    assert header.location == "./logs/run.eval"
    [r] = records
    assert r.probe_id == "q_globex_contract" and r.epoch == 2 and r.passed is False
    assert r.provenance_ok is True and r.refusal_ok is False
    assert r.expected_sources == ("globex.contract.crm", "globex.contract.note")
    assert r.consulted == ("globex.contract.crm",) and r.answer == "$1.2M"


def test_adapter_selects_score_by_axis_keys_regardless_of_scorer_name():
    s = _eval_sample("q1", 1, conflict_type="none", expected_behavior="answer", passed=True,
                     accuracy_ok=True, provenance_ok=True, refusal_ok=True, consulted=["crm"],
                     expected_sources=["crm"], answer="4 hours",
                     scorer_name="deterministic_reliability_scorer")
    header, [r] = eval_log_to_records(_eval_log([s], judge="deterministic", grader=None))
    assert header.engine == "deterministic" and header.grader is None
    assert r.passed is True


def test_header_records_scaffold_and_seed():
    # ADR-0009 made the prompt (-T scaffold=…) and ADR-0008 the org instance (-T seed=…)
    # run parameters; a header that drops them makes an R1/variant run indistinguishable
    # from a published baseline row everywhere downstream.
    s = _eval_sample("q1", 1, conflict_type="none", expected_behavior="answer", passed=True,
                     accuracy_ok=True, provenance_ok=True, refusal_ok=True, consulted=["crm"],
                     expected_sources=["crm"], answer="4 hours")
    log = _eval_log([s], task_args={"judge": "deterministic", "org": "meridian",
                                    "scaffold": "refusal_aware", "seed": "31337"})
    header, _ = eval_log_to_records(log)
    assert header.scaffold == "refusal_aware"
    assert header.seed == 31337  # -T seed=… arrives as a string from the inspect CLI


def test_header_scaffold_and_seed_default_for_pre_adr9_logs():
    # Logs that never passed -T scaffold/-T seed ran the baseline prompt on the
    # authored org — the task defaults — so the header says exactly that.
    s = _eval_sample("q1", 1, conflict_type="none", expected_behavior="answer", passed=True,
                     accuracy_ok=True, provenance_ok=True, refusal_ok=True, consulted=["crm"],
                     expected_sources=["crm"], answer="4 hours")
    header, _ = eval_log_to_records(_eval_log([s]))
    assert header.scaffold == "baseline" and header.seed == 0


def _answer_sample():
    return _eval_sample("q1", 1, conflict_type="none", expected_behavior="answer",
                        passed=True, accuracy_ok=True, provenance_ok=True, refusal_ok=True,
                        consulted=["crm"], expected_sources=["crm"], answer="4 hours")


def test_header_records_harness_when_an_ensemble_shim_sets_it():
    # An ensemble records its harness in task_args (ADR-0011); the header must carry it,
    # or the leaderboard cannot label an ensemble row as anything but a lone model.
    log = _eval_log([_answer_sample()],
                    task_args={"judge": "deterministic", "harness": "ensemble"})
    header, _ = eval_log_to_records(log)
    assert header.harness == "ensemble"


def test_header_harness_defaults_to_single():
    # RunHeader.harness is ALWAYS populated (unlike the nullable API field): a log with no
    # harness arg is a single-model run — every tessera_probes run is exactly that.
    header, _ = eval_log_to_records(_eval_log([_answer_sample()]))
    assert header.harness == "single"


def test_adapter_raises_on_no_samples():
    with pytest.raises(ReportError):
        eval_log_to_records(_eval_log([]))


def test_adapter_raises_on_foreign_log():
    from inspect_ai.log import EvalSample
    from inspect_ai.scorer import Score
    foreign = EvalSample(id="x", epoch=1, input="q", target="",
                         metadata={}, scores={"other": Score(value="C", metadata={"foo": 1})})
    with pytest.raises(ReportError):
        eval_log_to_records(_eval_log([foreign]))


def test_inspect_only_imported_by_adapter_and_cli():
    # The invariant is that the pure modules do not IMPORT inspect_ai. Parse the AST and
    # look for real import statements, so a docstring/comment that merely mentions
    # "inspect_ai" (e.g. "No inspect_ai") does not count as a leak.
    import ast
    import pathlib
    pkg = pathlib.Path(__file__).resolve().parents[1] / "src" / "tessera" / "report"
    offenders = []
    for f in sorted(pkg.glob("*.py")):
        if f.name in ("log_adapter.py", "cli.py"):
            continue
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.Import) and any(
                    n.name.split(".")[0] == "inspect_ai" for n in node.names):
                offenders.append(f.name)
            elif isinstance(node, ast.ImportFrom) and (
                    (node.module or "").split(".")[0] == "inspect_ai"):
                offenders.append(f.name)
    assert offenders == [], f"inspect_ai imported by pure modules: {sorted(set(offenders))}"


def test_cli_main_prints_report_to_stdout(tmp_path, capsys):
    from inspect_ai.log import write_eval_log
    from tessera.report.cli import main
    s = _eval_sample("q1", 1, conflict_type="none", expected_behavior="answer", passed=True,
                     accuracy_ok=True, provenance_ok=True, refusal_ok=True, consulted=["crm"],
                     expected_sources=["crm"], answer="4 hours")
    p = tmp_path / "run.eval"
    write_eval_log(_eval_log([s]), str(p))
    rc = main([str(p)])
    out = capsys.readouterr().out
    assert rc == 0 and "Tessera Reliability Report" in out


def test_cli_main_writes_to_out_file(tmp_path):
    from inspect_ai.log import write_eval_log
    from tessera.report.cli import main
    s = _eval_sample("q1", 1, conflict_type="none", expected_behavior="answer", passed=True,
                     accuracy_ok=True, provenance_ok=True, refusal_ok=True, consulted=["crm"],
                     expected_sources=["crm"], answer="4 hours")
    p = tmp_path / "run.eval"
    write_eval_log(_eval_log([s]), str(p))
    out_md = tmp_path / "report.md"
    rc = main([str(p), "-o", str(out_md)])
    assert rc == 0 and out_md.read_text().startswith("# Tessera Reliability Report")


def test_cli_main_missing_file_exits_2(capsys):
    from tessera.report.cli import main
    rc = main(["/nonexistent/path.eval"])
    err = capsys.readouterr().err
    assert rc == 2 and "cannot read log" in err


def _scorecard_log(task_args=None):
    # A fixed, path-independent single-model log for the byte-exact scorecard golden: fixed
    # location, deterministic samples. task_args lets a test flip on the harness dimension.
    samples = [
        _eval_sample("q_none", e, conflict_type="none", expected_behavior="answer",
                     passed=True, accuracy_ok=True, provenance_ok=True, refusal_ok=True,
                     consulted=["crm"], expected_sources=["crm"], answer="4 hours",
                     question="How long is onboarding?")
        for e in (1, 2, 3)
    ] + [
        _eval_sample("q_tie", e, conflict_type="unresolvable", expected_behavior="refuse",
                     passed=(e == 1), accuracy_ok=(e == 1), provenance_ok=True,
                     refusal_ok=(e == 1), consulted=["crm", "deal_desk"],
                     expected_sources=["crm", "deal_desk"],
                     answer=("cannot determine" if e == 1 else "$1.5M"),
                     question="What is the contract value?")
        for e in (1, 2, 3)
    ]
    return _eval_log(samples, judge="deterministic", grader=None,
                     task_args=(task_args if task_args is not None
                                else {"judge": "deterministic"}))


def test_scorecard_single_render_is_byte_identical_to_golden():
    # Backcompat for the second render surface: adding the conditional harness annotation
    # must not perturb a single-model scorecard (ADR-0011). Literal diff, fixed-location log.
    from pathlib import Path

    from tessera.report.cli import _build_report
    golden = (Path(__file__).resolve().parents[1]
              / "tests/fixtures/scorecard_single.golden.txt").read_text()
    assert _build_report(_scorecard_log()) == golden
    assert "Harness" not in golden          # no annotation when the run is a lone model


def test_scorecard_discloses_harness_when_not_single():
    # An ensemble scorecard must say so — the same disclosure rule as the leaderboard.
    from tessera.report.cli import _build_report
    log = _scorecard_log(task_args={"judge": "deterministic", "harness": "ensemble"})
    assert "**Harness:** ensemble" in _build_report(log)
