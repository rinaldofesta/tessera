"""Key-free tests for the leaderboard MANIFEST path (ADR-0010): docs/leaderboard.md is
a deterministic render of the committed docs/leaderboard.rows.json, never hand-edited.
The pure render path takes no logs; only the CLI tests touch disk."""

import json
from pathlib import Path

import pytest

from tessera.report.leaderboard import (
    leaderboard_rows, render_leaderboard, render_manifest,
)

_REPO = Path(__file__).resolve().parents[1]


def _report(model="anthropic/claude-sonnet-4-6", org="meridian", k=3,
            scorer_version="det-4", created="2026-06-11T17:26:31+00:00",
            pass_k=0.864, mean=0.909, categories=None, scaffold="baseline", seed=0,
            harness="single", answer_format_rate=0.985):
    cats = categories if categories is not None else {
        "none": 1.0, "resolvable": 1.0, "unresolvable": 0.4, "void": 1.0}
    return {
        "header": {"model": model, "engine": "deterministic", "grader": None, "org": org,
                   "k": k, "created": created, "location": "./logs/run.eval",
                   "scorer_version": scorer_version, "scaffold": scaffold, "seed": seed,
                   "harness": harness},
        "overall": {"pass_k_rate": pass_k, "mean_rate": mean},
        "categories": [{"key": key, "n_probes": 5, "pass_k_rate": rate,
                        "mean_rate": rate, "flaky": False} for key, rate in cats.items()],
        "axes": {"answer_format_rate": answer_format_rate},
        "probes": [],
    }


def _all_single_reports():
    # The exact set behind tests/fixtures/leaderboard_all_single.golden.txt. Kept here so
    # the golden and the assertion share one source; regenerate the golden from this.
    return [
        _report("anthropic/claude-sonnet-4-6", created="2026-06-11T17:00:00+00:00",
                pass_k=0.864, mean=0.909, answer_format_rate=0.985,
                categories={"none": 1.0, "resolvable": 1.0, "unresolvable": 0.4, "void": 1.0}),
        _report("openai/gpt-4o", created="2026-06-12T10:00:00+00:00",
                pass_k=0.455, mean=0.545, answer_format_rate=0.227,
                categories={"none": 0.0, "resolvable": 0.833, "unresolvable": 0.0, "void": 1.0}),
        _report("openai/gpt-4o-mini", created="2026-06-12T10:00:00+00:00",
                pass_k=0.273, mean=0.409, answer_format_rate=0.924,
                categories={"none": 0.0, "resolvable": 0.167, "unresolvable": 0.0, "void": 1.0}),
    ]


_ALL_SINGLE_NOTES = [None, "skips the CRM leg of cross-silo joins",
                     "fails the joins and all five ties"]


def _exhibition(label="moa/max (a+b to c)", pass_k=0.818, mean=0.894,
                categories=None, answer_format_rate=1.0, scorer_version="det-4",
                date="2026-07-06", notes="MoA ensemble", log=None):
    cats = categories if categories is not None else {
        "none": 0.667, "resolvable": 1.0, "unresolvable": 0.6, "void": 1.0}
    return {"label": label, "date": date, "pass_k_rate": pass_k, "mean_rate": mean,
            "categories": cats, "answer_format_rate": answer_format_rate,
            "scorer_version": scorer_version, "notes": notes, "log": log}


def test_manifest_path_reproduces_the_logs_path_for_baseline_rows():
    # The manifest rows ARE leaderboard_rows()-shaped; rendering them must be identical
    # to rendering straight from the report dicts. One render, two entry points.
    reports = [_report(),
               _report(model="openai/gpt-4o", pass_k=0.455, mean=0.545,
                       categories={"none": 0.0, "resolvable": 0.833,
                                   "unresolvable": 0.0, "void": 1.0})]
    from_manifest = render_manifest({"rows": leaderboard_rows(reports)})
    from_logs = render_leaderboard(reports)
    assert from_manifest == from_logs


def test_exhibitions_render_an_unranked_out_of_protocol_section():
    md = render_manifest({"rows": leaderboard_rows([_report()]),
                          "exhibitions": [_exhibition()]})
    assert "## Out-of-protocol exhibitions" in md
    assert "| Configuration | pass^3 |" in md          # unranked header, no rank column
    assert "moa/max (a+b to c)" in md and "MoA ensemble" in md
    # the exhibition sits AFTER the ranked table and BEFORE methodology
    assert md.index("| # | Model") < md.index("## Out-of-protocol") < md.index("## Methodology")
    # Post-ADR-0011 the section is for DIFFERENT-protocol configs, not ensembles (which now
    # rank in the table with harness disclosed). Pin the new framing so it can't regress.
    assert "ran a DIFFERENT protocol" in md
    assert "not comparable" in md
    assert "An ensemble is not here" in md


def test_no_exhibition_section_when_none_present():
    md = render_manifest({"rows": leaderboard_rows([_report()])})
    assert "Out-of-protocol" not in md


def test_exhibitions_bypass_the_uniformity_guard():
    # An exhibition is out-of-protocol by definition: it may carry a different scorer
    # label than the ranked rows without tripping the ADR-0006 guard.
    md = render_manifest({"rows": leaderboard_rows([_report()]),
                          "exhibitions": [_exhibition(scorer_version="moa-shim-1")]})
    assert "moa-shim-1" in md


def test_manifest_path_still_enforces_the_guard_on_ranked_rows():
    # The guard is not bypassed just because rows arrive from a manifest instead of logs.
    bad = leaderboard_rows([_report()]) + leaderboard_rows(
        [_report(model="openai/gpt-4o", scorer_version="llm-2")])
    with pytest.raises(ValueError, match="scorer_version"):
        render_manifest({"rows": bad})


def test_committed_manifest_renders_to_the_committed_markdown():
    # THE keystone invariant (ADR-0010), and exactly what CI enforces: docs/leaderboard.md
    # is a byte-for-byte render of docs/leaderboard.rows.json. Fails the instant either is
    # hand-edited out of sync.
    manifest = json.loads((_REPO / "docs/leaderboard.rows.json").read_text())
    expected = (_REPO / "docs/leaderboard.md").read_text()
    assert render_manifest(manifest) == expected


def _write_eval_log(path):
    from inspect_ai.log import (
        EvalConfig, EvalDataset, EvalLog, EvalSample, EvalSpec, write_eval_log,
    )
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
    write_eval_log(EvalLog(eval=spec, samples=samples, location=str(path)), str(path))


def test_cli_extract_emits_manifest_rows_with_a_log_digest(tmp_path):
    from tessera.report.cli import leaderboard_main
    log = tmp_path / "run.eval"
    _write_eval_log(log)
    out = tmp_path / "row.json"
    assert leaderboard_main(["--extract", str(log), "-o", str(out)]) == 0
    rows = json.loads(out.read_text())
    assert len(rows) == 1
    row = rows[0]
    assert row["model"] == "anthropic/claude-sonnet-4-6" and row["scorer_version"] == "det-4"
    assert len(row["log"]) == 64                       # sha256 hex of the source log
    # the extracted row renders back through the manifest path
    assert "det-4" in render_manifest({"rows": rows})


def test_cli_manifest_writes_markdown(tmp_path):
    from tessera.report.cli import leaderboard_main
    manifest = {"rows": leaderboard_rows([_report()]), "exhibitions": [_exhibition()]}
    mpath = tmp_path / "rows.json"
    mpath.write_text(json.dumps(manifest))
    out = tmp_path / "leaderboard.md"
    assert leaderboard_main(["--manifest", str(mpath), "-o", str(out)]) == 0
    md = out.read_text()
    assert "## Out-of-protocol exhibitions" in md and "det-4" in md


# --- harness as a displayed comparability axis (ADR-0011) --------------------------

def _row_line(md, needle):
    return next(l for l in md.splitlines() if l.startswith("| ") and needle in l)


def test_all_single_render_is_byte_identical_to_golden():
    # Load-bearing backcompat: the conditional harness column must not perturb a table
    # with no ensembles — not the separator, not alignment, not one byte. Literal diff.
    golden = (_REPO / "tests/fixtures/leaderboard_all_single.golden.txt").read_text()
    assert render_leaderboard(_all_single_reports(), notes=_ALL_SINGLE_NOTES) == golden
    assert "harness" not in golden.lower()   # no column when every row is single


def test_harness_column_interleaves_ensemble_with_singles_by_pass_k():
    # The ensemble is ranked by the SAME metric as everyone else — no segregation, even in
    # ordering: sonnet-4-6 (0.864) > moa (0.818) > sonnet-5 (0.773).
    reports = [
        _report("anthropic/claude-sonnet-4-6", pass_k=0.864, mean=0.909),
        _report("moa/max (a+b to c)", pass_k=0.818, mean=0.894, harness="ensemble"),
        _report("anthropic/claude-sonnet-5", pass_k=0.773, mean=0.864),
    ]
    md = render_leaderboard(reports)
    assert _row_line(md, "claude-sonnet-4-6").startswith("| 1 |")
    assert _row_line(md, "moa/max").startswith("| 2 |")        # interleaved, not appended
    assert _row_line(md, "claude-sonnet-5").startswith("| 3 |")
    # the harness column labels each row for what it is
    assert "ensemble" in _row_line(md, "moa/max")
    assert "single" in _row_line(md, "claude-sonnet-4-6")


def test_harness_is_a_displayed_axis_not_a_guarded_dimension():
    # Unlike scaffold/seed, a table MAY mix harnesses (they ran the identical protocol, so
    # they are comparable). render must not raise, and the column must label both — neutral
    # model names so the labels can only come from the harness column, not a substring.
    md = render_leaderboard([_report("m/alpha", pass_k=0.9, mean=0.95),
                             _report("m/beta", pass_k=0.8, mean=0.85, harness="ensemble")])
    assert "single" in _row_line(md, "m/alpha")
    assert "ensemble" in _row_line(md, "m/beta")


def test_harness_disclosure_names_the_identical_protocol():
    # The disclosure must say "identical protocol" (all five guarded dims), not a partial
    # "same org/scorer/k" — the row ranks precisely because it matched every guarded dim.
    md = render_leaderboard([_report(pass_k=0.9, mean=0.95),
                             _report("moa/x", pass_k=0.8, mean=0.85, harness="ensemble")])
    assert "identical protocol" in md
    assert "org, k, scorer, scaffold, seed" in md
