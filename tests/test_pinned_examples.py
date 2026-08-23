"""Smoke tests over the committed demo logs in examples/ — the project's public evidence.

These are the numbers the README and lessons cite; nothing else loads the pinned files,
so an inspect_ai schema change (or an accidental re-pin) could silently break the demo.
Pure local file reads through the exact shared pipeline behind the CLI and the API
(report_to_dict); key-free and fast (~0.5s for both).
"""

import hashlib
import json
import re
from pathlib import Path

import pytest
from inspect_ai.log import read_eval_log

from tessera.compiler import build_artifacts
from tessera.examples.toy_org import build_toy_blueprint
from tessera.report.log_adapter import eval_log_to_records
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
    log = read_eval_log(str(eval_path), resolve_attachments=True)
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


def test_first_contact_log_contains_no_credential_like_strings():
    log = read_eval_log(str(EXAMPLES / "first-contact.eval"), resolve_attachments=True)
    pattern = re.compile(
        r"api[_-]?key|authorization|bearer\s+[A-Za-z0-9]|sk-[A-Za-z0-9]|"
        r"session[_-]?token|cookie|client_secret|private_key",
        re.IGNORECASE,
    )
    matches = []

    def walk(value, path="$"):
        if isinstance(value, dict):
            for key, nested in value.items():
                walk(nested, f"{path}.{key}")
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                walk(nested, f"{path}[{index}]")
        elif isinstance(value, str) and pattern.search(value):
            matches.append(path)

    walk(log.model_dump(mode="json"))
    assert matches == []
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
