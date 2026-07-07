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
        "axes": {"answer_format_rate": 0.985},
        "probes": [],
    }


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
