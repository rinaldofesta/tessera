"""Smoke tests over the committed demo logs in examples/ — the project's public evidence.

These are the numbers the README and lessons cite; nothing else loads the pinned files,
so an inspect_ai schema change (or an accidental re-pin) could silently break the demo.
Pure local file reads through the exact shared pipeline behind the CLI and the API
(report_to_dict); key-free and fast (~0.5s for both).
"""

import hashlib
import json
from functools import cache
from pathlib import Path

import pytest
from inspect_ai.log import read_eval_log

from tessera.compiler import build_artifacts
from tessera.credential_scan import find_credential_like_values
from tessera.examples.toy_org import build_toy_blueprint
from tessera.report.log_adapter import eval_log_to_records
from tessera.report.serialize import report_to_dict

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@cache
def _load_log(path: str):
    return read_eval_log(path, resolve_attachments=True)


def _report(name: str) -> dict:
    return report_to_dict(_load_log(str(EXAMPLES / name)))


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


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def test_first_contact_receipt_pins_files_and_semantically_matches_toy_org():
    receipt = json.loads((EXAMPLES / "first-contact.receipt.json").read_text())
    eval_path = EXAMPLES / "first-contact.eval"
    report_path = EXAMPLES / "first-contact-report.md"
    assert hashlib.sha256(eval_path.read_bytes()).hexdigest() == receipt["eval"]["sha256"]
    assert hashlib.sha256(report_path.read_bytes()).hexdigest() == receipt["report"]["sha256"]

    blueprint = build_toy_blueprint()
    assert _canonical_sha256(blueprint.model_dump(mode="json")) == (
        receipt["toy_org"]["canonical_blueprint_sha256"])
    assert _canonical_sha256(build_artifacts(blueprint)) == (
        receipt["toy_org"]["compiled_artifacts_sha256"])

    # The run identifies a dirty Git tree, so byte-for-byte source reconstruction is not
    # possible. Pin the stronger claim the evidence supports: its full scoring contract is
    # object-for-object equal to today's committed toy blueprint.
    log = _load_log(str(eval_path))
    assert log.eval.revision.commit == receipt["run"]["git_revision"]
    assert log.eval.revision.dirty is receipt["run"]["git_dirty"]
    _, records = eval_log_to_records(log)
    expected = {probe.probe_id: probe for probe in blueprint.probes}
    assert set(record.probe_id for record in records) == set(expected)
    for record in records:
        probe = expected[record.probe_id]
        assert record.question == probe.question
        assert record.conflict_type == probe.conflict_type.value
        assert record.expected_behavior == probe.expected_behavior.value
        assert record.expected_answer == probe.expected_answer
        assert record.expected_sources == tuple(probe.expected_sources)


@pytest.mark.parametrize("eval_path", sorted(EXAMPLES.glob("*.eval")), ids=lambda path: path.name)
def test_committed_eval_logs_contain_no_credential_like_values(eval_path):
    log = _load_log(str(eval_path))
    assert find_credential_like_values(log.model_dump(mode="json")) == []


def test_first_contact_log_pins_public_origin():
    log = _load_log(str(EXAMPLES / "first-contact.eval"))
    assert log.eval.revision.origin == "https://github.com/rinaldofesta/tessera.git"


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
