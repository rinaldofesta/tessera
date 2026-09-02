"""Key-free tests for the leaderboard generator (report.leaderboard + tessera CLI).
The pure module consumes report_to_dict-shaped dicts; only the CLI test
fabricates an EvalLog on disk — no model calls, no network."""

import pytest
from typer.testing import CliRunner

from tessera.cli import app
from tessera.report.leaderboard import leaderboard_rows, render_leaderboard


def _report(model="anthropic/claude-sonnet-4-6", org="meridian", k=3,
            scorer_version="det-4", created="2026-06-11T17:26:31+00:00",
            pass_k=0.864, mean=0.909, categories=None, scaffold="baseline", seed=0):
    cats = categories if categories is not None else {
        "none": 1.0, "resolvable": 1.0, "unresolvable": 0.4, "void": 1.0}
    return {
        "header": {"model": model, "engine": "deterministic", "grader": None, "org": org,
                   "k": k, "created": created, "location": "./logs/run.eval",
                   "scorer_version": scorer_version, "scaffold": scaffold, "seed": seed},
        "overall": {"pass_k_rate": pass_k, "mean_rate": mean},
        "categories": [{"key": key, "n_probes": 5, "pass_k_rate": rate,
                        "mean_rate": rate, "flaky": False} for key, rate in cats.items()],
        "probes": [],
    }


def test_row_from_report_dict():
    (row,) = leaderboard_rows([_report()])
    assert row["label"] == "anthropic/claude-sonnet-4-6"
    assert row["date"] == "2026-06-11"
    assert row["pass_k_rate"] == 0.864 and row["mean_rate"] == 0.909
    assert row["scorer_version"] == "det-4" and row["k"] == 3 and row["org"] == "meridian"
    assert row["categories"]["unresolvable"] == 0.4


def test_rows_sorted_by_pass_k_desc():
    weaker = _report(model="openai/gpt-4o-mini", pass_k=0.5, mean=0.7)
    rows = leaderboard_rows([weaker, _report()])
    assert [r["label"] for r in rows] == [
        "anthropic/claude-sonnet-4-6", "openai/gpt-4o-mini"]


def test_per_category_columns_canonical_order():
    # Distinct rates per category, fed in scrambled order: the rendered cells must
    # land in canonical none/resolvable/unresolvable/void order regardless.
    scrambled = {"void": 0.1, "none": 0.4, "unresolvable": 0.2, "resolvable": 0.3}
    md = render_leaderboard([_report(categories=scrambled)])
    header_line = next(line for line in md.splitlines() if "| none |" in line)
    assert "| none | resolvable | unresolvable | void |" in header_line
    row_line = next(line for line in md.splitlines() if "claude-sonnet-4-6" in line)
    cells = [c.strip() for c in row_line.split("|")]
    i = cells.index("40%")
    assert cells[i:i + 4] == ["40%", "30%", "20%", "10%"]


def test_refuses_mixed_scorer_versions():
    with pytest.raises(ValueError, match="scorer_version"):
        leaderboard_rows([_report(), _report(model="openai/gpt-4o",
                                             scorer_version="llm-2")])


def test_refuses_mixed_org_or_k():
    with pytest.raises(ValueError, match="org"):
        leaderboard_rows([_report(), _report(model="openai/gpt-4o", org="toy")])
    with pytest.raises(ValueError, match="k"):
        leaderboard_rows([_report(), _report(model="openai/gpt-4o", k=2)])


def test_refuses_mixed_scaffold_or_seed():
    # ADR-0009 made the prompt a task parameter, opening the exact dimension the freeze
    # exists to close: an R1 run scores ~20 points higher on the same org and must never
    # mix into a B0 table. Same for factory seeds — a different seed is a different org
    # instance with a different answer key (ADR-0008).
    with pytest.raises(ValueError, match="scaffold"):
        leaderboard_rows([_report(),
                          _report(model="openai/gpt-4o", scaffold="refusal_aware")])
    with pytest.raises(ValueError, match="seed"):
        leaderboard_rows([_report(), _report(model="openai/gpt-4o", seed=3)])


def test_pre_scaffold_report_dicts_default_to_baseline_seed_zero():
    # Dicts serialized before ADR-0009 carry no scaffold/seed keys; they were produced
    # by the baseline prompt on the authored org, so they pair with explicit ones.
    old = _report()
    del old["header"]["scaffold"], old["header"]["seed"]
    assert len(leaderboard_rows([old, _report(model="openai/gpt-4o")])) == 2


def test_repro_block_pins_the_scaffold_arm_and_seed():
    md = render_leaderboard([_report()])
    assert "-T seed=0 -T scaffold=baseline" in md


def test_non_baseline_scaffold_is_disclosed():
    md = render_leaderboard([_report(scaffold="refusal_aware"),
                             _report(model="openai/gpt-4o", scaffold="refusal_aware")])
    assert "non-baseline scaffold" in md


def test_methodology_block_present():
    md = render_leaderboard([_report()])
    assert "Results as of 2026-06-11" in md          # date stamp from the latest run
    assert "blueprint is public" in md               # the ADR-0006 contamination stance
    assert "0006-meridian-and-the-leaderboard-protocol.md" in md
    assert "pass^3" in md and "det-4" in md


def test_label_override():
    md = render_leaderboard(
        [_report(), _report(created="2026-06-12T09:00:00+00:00", pass_k=0.6, mean=0.8)],
        labels=["claude-sonnet-4-6 (direct)", "claude-sonnet-4-6 (delegated)"])
    assert "claude-sonnet-4-6 (direct)" in md
    assert "claude-sonnet-4-6 (delegated)" in md


def test_answer_format_column_from_axes():
    rep = _report()
    rep["axes"] = {"answer_format_rate": 0.985}
    md = render_leaderboard([rep])
    assert "ANSWER fmt" in md and "98.5%" in md
    # absent on old logs -> em dash, never a crash
    assert "—" in render_leaderboard([_report()])


def test_notes_column_carries_provided_note():
    md = render_leaderboard([_report(model="ollama/qwen3.5:latest")],
                            notes=["open-weights, 9.7B, Q4_K_M, local via Ollama"])
    assert "open-weights, 9.7B, Q4_K_M, local via Ollama" in md


def _fabricated_eval_log():
    # Self-contained fabrication (same idiom as test_serialize.py): no model calls.
    from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSample, EvalSpec
    from inspect_ai.scorer import Score

    samples = [
        EvalSample(
            id="q1", epoch=e, input="Q?", target="4 hours",
            metadata={"conflict_type": "none", "expected_behavior": "answer",
                      "expected_answer": "4 hours", "expected_sources": ["crm"]},
            scores={"deterministic_reliability_scorer": Score(
                value="C", answer="4 hours",
                metadata={"passed": True, "accuracy_ok": True, "provenance_ok": True,
                          "refusal_ok": True, "consulted": ["crm"],
                          "scorer_version": "det-4"})})
        for e in (1, 2, 3)
    ]
    spec = EvalSpec(created="2026-06-12T10:00:00+00:00", task="tessera_probes",
                    dataset=EvalDataset(), model="anthropic/claude-sonnet-4-6",
                    config=EvalConfig(epochs=3),
                    task_args={"judge": "deterministic", "org": "meridian", "k": 3})
    return EvalLog(eval=spec, samples=samples, location="./logs/run.eval")


def test_cli_writes_markdown_from_eval_logs(tmp_path):
    from inspect_ai.log import write_eval_log

    p = tmp_path / "run.eval"
    write_eval_log(_fabricated_eval_log(), str(p))

    out = tmp_path / "leaderboard.md"
    result = CliRunner().invoke(
        app,
        ["leaderboard", "render", str(p), "--label", "sonnet-smoke", "-o", str(out)],
    )
    assert result.exit_code == 0
    md = out.read_text()
    assert "sonnet-smoke" in md and "det-4" in md and "Results as of" in md
