"""Key-free tests for the leaderboard generator (report.leaderboard + the CLI in
report.cli). The pure module consumes report_to_dict-shaped dicts; only the CLI test
fabricates an EvalLog on disk — no model calls, no network."""

import pytest

from tessera.report.leaderboard import leaderboard_rows, render_leaderboard


def _report(model="anthropic/claude-sonnet-4-6", org="meridian", k=3,
            scorer_version="det-4", created="2026-06-11T17:26:31+00:00",
            pass_k=0.864, mean=0.909, categories=None):
    cats = categories if categories is not None else {
        "none": 1.0, "resolvable": 1.0, "unresolvable": 0.4, "void": 1.0}
    return {
        "header": {"model": model, "engine": "deterministic", "grader": None, "org": org,
                   "k": k, "created": created, "location": "./logs/run.eval",
                   "scorer_version": scorer_version},
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
    header_line = next(l for l in md.splitlines() if "| none |" in l)
    assert "| none | resolvable | unresolvable | void |" in header_line
    row_line = next(l for l in md.splitlines() if "claude-sonnet-4-6" in l)
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


def test_notes_column_carries_provided_note():
    md = render_leaderboard([_report(model="ollama/qwen3.5:latest")],
                            notes=["open-weights, 9.7B, Q4_K_M, local via Ollama"])
    assert "open-weights, 9.7B, Q4_K_M, local via Ollama" in md


def test_cli_writes_markdown_from_eval_logs(tmp_path):
    from inspect_ai.log import write_eval_log

    from tessera.report.cli import leaderboard_main
    from tests.test_serialize import _eval_log, _eval_sample

    samples = [
        _eval_sample("q1", e, conflict_type="none", expected_behavior="answer",
                     passed=True, accuracy_ok=True, provenance_ok=True, refusal_ok=True,
                     consulted=["crm"], expected_sources=["crm"], answer="4 hours",
                     scorer_name="deterministic_reliability_scorer", scorer_version="det-4")
        for e in (1, 2, 3)
    ]
    log = _eval_log(samples, judge="deterministic", grader=None)
    log.eval.task_args["org"] = "meridian"
    log.eval.task_args["k"] = 3
    p = tmp_path / "run.eval"
    write_eval_log(log, str(p))

    out = tmp_path / "leaderboard.md"
    rc = leaderboard_main([str(p), "--label", "sonnet-smoke", "-o", str(out)])
    assert rc == 0
    md = out.read_text()
    assert "sonnet-smoke" in md and "det-4" in md and "Results as of" in md
