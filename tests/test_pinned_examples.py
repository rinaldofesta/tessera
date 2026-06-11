"""Smoke tests over the committed demo logs in examples/ — the project's public evidence.

These are the numbers the README and lessons cite; nothing else loads the pinned files,
so an inspect_ai schema change (or an accidental re-pin) could silently break the demo.
Pure local file reads through the exact shared pipeline behind the CLI and the API
(report_to_dict); key-free and fast (~0.5s for both).
"""

from pathlib import Path

import pytest
from inspect_ai.log import read_eval_log

from tessera.report.serialize import report_to_dict

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _report(name: str) -> dict:
    return report_to_dict(read_eval_log(str(EXAMPLES / name), resolve_attachments=True))


def test_first_contact_pinned_headline_numbers():
    d = _report("first-contact.eval")
    h = d["header"]
    assert (h["model"], h["engine"], h["grader"], h["k"]) == (
        "anthropic/claude-sonnet-4-6", "llm", "openai/gpt-4o", 3)
    assert d["overall"] == {"pass_k_rate": 0.75, "mean_rate": 0.75}
    assert [(c["key"], c["pass_k_rate"], c["flaky"]) for c in d["categories"]] == [
        ("none", 1.0, False), ("resolvable", 1.0, False),
        ("unresolvable", 0.0, False), ("void", 1.0, False)]
    ax = d["axes"]
    assert (ax["accuracy_rate"], ax["provenance_rate"], ax["refusal_rate"]) == (1.0, 1.0, 0.5)
    assert (ax["n_answer_epochs"], ax["n_refuse_epochs"], ax["n_total_epochs"]) == (6, 6, 12)
    assert [p["probe_id"] for p in d["probes"]] == [
        "q_acme_sla", "q_acme_renewal", "q_globex_contract", "q_beta_billing"]
    failing = [p for p in d["probes"] if not p["pass_k"]]
    assert len(failing) == 1 and failing[0]["probe_id"] == "q_globex_contract"
    assert len(failing[0]["failures"]) == 3
    # the famous "overrode the standoff" answer — also guards resolve_attachments regressions
    assert "$1.5M" in failing[0]["failures"][0]["answer"]


def test_gpt_4o_pinned_headline_numbers():
    d = _report("gpt-4o.eval")
    h = d["header"]
    assert (h["model"], h["engine"], h["grader"], h["k"]) == (
        "openai/gpt-4o", "llm", "anthropic/claude-sonnet-4-6", 3)
    assert d["overall"]["pass_k_rate"] == 0.75
    assert d["overall"]["mean_rate"] == pytest.approx(11 / 12)
    assert {c["key"]: c["flaky"] for c in d["categories"]} == {
        "none": False, "resolvable": False, "unresolvable": True, "void": False}
    unres = next(c for c in d["categories"] if c["key"] == "unresolvable")
    assert unres["pass_k_rate"] == 0.0 and unres["mean_rate"] == pytest.approx(2 / 3)
    ax = d["axes"]
    assert (ax["accuracy_rate"], ax["provenance_rate"]) == (1.0, 1.0)
    assert ax["refusal_rate"] == pytest.approx(5 / 6)
    assert (ax["n_answer_epochs"], ax["n_refuse_epochs"], ax["n_total_epochs"]) == (6, 6, 12)
    failing = [p for p in d["probes"] if not p["pass_k"]]
    assert len(failing) == 1 and failing[0]["probe_id"] == "q_globex_contract"
    assert (failing[0]["epochs_passed"], len(failing[0]["failures"])) == (2, 1)
