"""Key-free tests for report.serialize.report_to_dict. Fabricates EvalLogs in-memory
(same helpers as test_report.py) — no model calls, no network."""

from tessera.report.serialize import report_to_dict


def _eval_log(samples, *, judge="llm", epochs=3, grader="openai/gpt-4o",
              model="anthropic/claude-sonnet-4-6", location="./logs/run.eval",
              packages={"inspect_ai": "0.3.235"}):
    from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSpec
    from inspect_ai.model import ModelConfig
    roles = {"grader": ModelConfig(model=grader)} if grader else {}
    spec = EvalSpec(created="2026-06-03T10:00:00+00:00", task="tessera_probes",
                    dataset=EvalDataset(), model=model, config=EvalConfig(epochs=epochs),
                    task_args={"judge": judge}, model_roles=roles, packages=packages)
    return EvalLog(eval=spec, samples=samples, location=location)


def _eval_sample(probe_id, epoch, *, conflict_type, expected_behavior, passed, accuracy_ok,
                 provenance_ok, refusal_ok, consulted, expected_sources, answer,
                 scorer_name="llm_reliability_scorer", question="Q?", expected_answer=None,
                 scorer_version=None, answer_format_ok=None):
    from inspect_ai.log import EvalSample
    from inspect_ai.scorer import Score
    score_meta = {"passed": passed, "accuracy_ok": accuracy_ok,
                  "provenance_ok": provenance_ok, "refusal_ok": refusal_ok,
                  "consulted": list(consulted)}
    if scorer_version is not None:
        score_meta["scorer_version"] = scorer_version
    if answer_format_ok is not None:
        score_meta["answer_format_ok"] = answer_format_ok
    return EvalSample(
        id=probe_id, epoch=epoch, input=question, target=expected_answer or "",
        metadata={"conflict_type": conflict_type, "expected_behavior": expected_behavior,
                  "expected_answer": expected_answer, "expected_sources": list(expected_sources)},
        scores={scorer_name: Score(value=("C" if passed else "I"), answer=answer,
                metadata=score_meta)})


def _answer(probe_id, epoch, conflict_type, passed):
    return _eval_sample(probe_id, epoch, conflict_type=conflict_type, expected_behavior="answer",
                        passed=passed, accuracy_ok=passed, provenance_ok=True, refusal_ok=True,
                        consulted=["crm"], expected_sources=["crm"], answer="4 hours")


def test_header_and_overall():
    log = _eval_log([_answer("q1", 1, "none", True), _answer("q1", 2, "none", True)])
    d = report_to_dict(log)
    assert d["header"]["model"] == "anthropic/claude-sonnet-4-6"
    assert d["header"]["engine"] == "llm" and d["header"]["grader"] == "openai/gpt-4o"
    assert d["header"]["k"] == 3 and d["header"]["location"] == "./logs/run.eval"
    assert d["overall"]["pass_k_rate"] == 1.0 and d["overall"]["mean_rate"] == 1.0
    # the producing inspect_ai version is recorded for reproducibility (read from the log's
    # eval.packages); None when the log didn't record it
    assert d["header"]["inspect_ai_version"] == "0.3.235"


def test_inspect_ai_version_is_none_when_unrecorded():
    log = _eval_log([_answer("q1", 1, "none", True)], packages={})
    assert report_to_dict(log)["header"]["inspect_ai_version"] is None


def test_categories_canonical_order_and_flaky():
    # one consistent 'none' probe (pass_k), one flaky 'resolvable' probe (2/3)
    samples = [
        _answer("q_none", 1, "none", True), _answer("q_none", 2, "none", True),
        _answer("q_none", 3, "none", True),
        _answer("q_res", 1, "resolvable", True), _answer("q_res", 2, "resolvable", False),
        _answer("q_res", 3, "resolvable", True),
    ]
    d = report_to_dict(_eval_log(samples))
    keys = [c["key"] for c in d["categories"]]
    assert keys == ["none", "resolvable"]          # canonical order, absent categories dropped
    res = next(c for c in d["categories"] if c["key"] == "resolvable")
    assert res["pass_k_rate"] == 0.0 and abs(res["mean_rate"] - 2 / 3) < 1e-9
    assert res["flaky"] is True                    # mean > pass_k
    none = next(c for c in d["categories"] if c["key"] == "none")
    assert none["flaky"] is False


def test_axes_null_when_no_refuse_epochs():
    d = report_to_dict(_eval_log([_answer("q1", 1, "none", True)]))
    assert d["axes"]["refusal_rate"] is None       # n/a, not a fake 0%
    assert d["axes"]["accuracy_rate"] == 1.0
    assert d["axes"]["n_refuse_epochs"] == 0 and d["axes"]["n_answer_epochs"] == 1


def test_probe_failures_carry_missing_sources():
    fail = _eval_sample("q_acme_renewal", 2, conflict_type="resolvable",
                        expected_behavior="answer", passed=False, accuracy_ok=True,
                        provenance_ok=False, refusal_ok=True, consulted=["crm"],
                        expected_sources=["crm", "acme.renewal.note"],
                        answer="2026-03-01 (per CRM)", question="When is Acme's renewal?")
    ok = _eval_sample("q_acme_renewal", 1, conflict_type="resolvable",
                      expected_behavior="answer", passed=True, accuracy_ok=True,
                      provenance_ok=True, refusal_ok=True, consulted=["crm", "acme.renewal.note"],
                      expected_sources=["crm", "acme.renewal.note"], answer="2026-03-01")
    d = report_to_dict(_eval_log([fail, ok]))
    [probe] = d["probes"]
    assert probe["probe_id"] == "q_acme_renewal" and probe["pass_k"] is False
    assert len(probe["failures"]) == 1
    f = probe["failures"][0]
    assert f["epoch"] == 2 and f["missing"] == ["acme.renewal.note"]
    assert f["consulted"] == ["crm"]


def test_full_probes_list_includes_passing_probes():
    d = report_to_dict(_eval_log([_answer("q1", 1, "none", True)]))
    assert len(d["probes"]) == 1 and d["probes"][0]["failures"] == []


def test_scorer_version_and_format_rate_surface_when_recorded():
    # det-engine logs stamp scorer_version + answer_format_ok; the scorecard shows them
    samples = [
        _eval_sample("q1", 1, conflict_type="none", expected_behavior="answer",
                     passed=True, accuracy_ok=True, provenance_ok=True, refusal_ok=True,
                     consulted=["c"], expected_sources=["c"], answer="ANSWER: 4 hours",
                     scorer_version="det-4", answer_format_ok=True),
        _eval_sample("q1", 2, conflict_type="none", expected_behavior="answer",
                     passed=False, accuracy_ok=False, provenance_ok=True, refusal_ok=True,
                     consulted=["c"], expected_sources=["c"], answer="four-ish hours",
                     scorer_version="det-4", answer_format_ok=False),
    ]
    d = report_to_dict(_eval_log(samples, judge="deterministic", grader=None))
    assert d["header"]["scorer_version"] == "det-4"
    assert d["axes"]["answer_format_rate"] == 0.5
    [probe] = d["probes"]
    assert probe["failures"][0]["answer_format_ok"] is False


def test_scorer_version_and_format_rate_null_on_old_logs():
    # pre-det-2 logs (and llm-1 logs) never recorded either field — null, not fake values
    d = report_to_dict(_eval_log([_answer("q1", 1, "none", True)]))
    assert d["header"]["scorer_version"] is None
    assert d["axes"]["answer_format_rate"] is None


def test_header_org_present_when_recorded_else_none():
    from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSpec
    spec = EvalSpec(created="2026-06-08T00:00:00+00:00", task="tessera_probes",
                    dataset=EvalDataset(), model="m", config=EvalConfig(epochs=3),
                    task_args={"judge": "deterministic", "org": "acme"}, model_roles={})
    log = EvalLog(eval=spec, samples=[_answer("q1", 1, "none", True)], location="x.eval")
    assert report_to_dict(log)["header"]["org"] == "acme"
    # without org in task_args -> None (e.g. pre-org logs)
    assert report_to_dict(_eval_log([_answer("q1", 1, "none", True)]))["header"]["org"] is None
