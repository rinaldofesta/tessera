from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest
from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSample, EvalSpec, write_eval_log
from inspect_ai.scorer import Score
from typer.testing import CliRunner

from tessera.api.providers import PROVIDERS
from tessera.cli import app
from tessera.store import RunStore

RUNNER = CliRunner()
BUNDLED_LOG = (
    Path(__file__).parents[1]
    / "src"
    / "tessera"
    / "data"
    / "examples"
    / "first-contact"
    / "log.eval"
)
FIRST_CONTACT_SENTENCE = (
    "Not reliable. Right every time on 3 of 4 questions. "
    "1 question is never right. Trouble spot: genuine disagreement."
)


@pytest.fixture(autouse=True)
def _isolated_cli_home(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("TESSERA_ENV_FILE", raising=False)
    for spec in PROVIDERS.values():
        for field in spec.fields:
            monkeypatch.delenv(field.env_var, raising=False)


def _json(result) -> dict:
    payload, end = json.JSONDecoder().raw_decode(result.stdout)
    assert result.stdout[end:].strip() == ""
    assert isinstance(payload, dict)
    return payload


def _spec() -> dict:
    return {
        "suite": "starter",
        "model": "ollama/test",
        "engine": "deterministic",
        "grader": None,
        "k": 1,
        "scaffold": "baseline",
        "seed": 0,
    }


def _fake_log(location: str, *, passed: bool) -> EvalLog:
    sample = EvalSample(
        id="q1",
        epoch=1,
        input="What is the SLA?",
        target="4 hours",
        metadata={
            "conflict_type": "none",
            "expected_behavior": "answer",
            "expected_answer": "4 hours",
            "expected_sources": ["crm"],
        },
        scores={
            "llm_reliability_scorer": Score(
                value="C" if passed else "I",
                answer="4 hours" if passed else "unknown",
                metadata={
                    "passed": passed,
                    "accuracy_ok": passed,
                    "provenance_ok": True,
                    "refusal_ok": True,
                    "consulted": ["crm"],
                    "scorer_version": "det-4",
                    "answer_format_ok": passed,
                },
            )
        },
    )
    spec = EvalSpec(
        created="2026-09-02T10:00:00+00:00",
        task="tessera_probes",
        dataset=EvalDataset(),
        model="ollama/test",
        config=EvalConfig(epochs=1),
        task_args={
            "judge": "deterministic",
            "org": "toy",
            "k": 1,
            "scaffold": "baseline",
            "seed": 0,
        },
        model_roles={},
        packages={"inspect_ai": "0.3.235"},
    )
    return EvalLog(eval=spec, samples=[sample], location=location)


def _writing_eval(passed: bool):
    def evaluate(**kwargs):
        location = str(Path(kwargs["log_dir"]) / "inspect-output.eval")
        log = _fake_log(location, passed=passed)
        write_eval_log(log, location)
        return log

    return evaluate


def test_no_args_shows_successful_help_and_version():
    result = RUNNER.invoke(app)

    assert result.exit_code == 0
    assert "run" in result.stdout and "report" in result.stdout
    version = RUNNER.invoke(app, ["--version"])
    assert version.exit_code == 0 and version.stdout.startswith("tessera ")


def test_report_bundled_human_and_json():
    human = RUNNER.invoke(app, ["report", "first-contact"])
    encoded = RUNNER.invoke(app, ["report", "first-contact", "--json"])

    assert human.exit_code == 0 and "75%" in human.stdout
    payload = _json(encoded)
    assert encoded.exit_code == 0 and payload["ok"] is True
    assert payload["verdict"]["sentence"] == FIRST_CONTACT_SENTENCE


def test_report_raw_eval_does_not_import_it(monkeypatch):
    home = Path(os.environ["TESSERA_HOME"])
    result = RUNNER.invoke(app, ["report", str(BUNDLED_LOG)])

    assert result.exit_code == 0 and "75%" in result.stdout
    assert not (home / "runs").exists()


def test_dry_run_json_is_advisory_with_a_fix():
    result = RUNNER.invoke(
        app,
        ["run", "--model", "anthropic/claude-sonnet-4-6", "--dry-run", "--json"],
    )

    payload = _json(result)
    assert result.exit_code == 0 and payload["ready"] is False
    assert payload["blockers"][0]["fix"] == "tessera connect anthropic"


def test_run_uses_stable_not_connected_and_spec_exit_codes():
    disconnected = RUNNER.invoke(
        app,
        ["run", "--model", "anthropic/claude-sonnet-4-6"],
    )
    bad_suite = RUNNER.invoke(
        app,
        ["run", "--model", "ollama/test", "--suite", "nope"],
    )

    assert disconnected.exit_code == 2
    assert bad_suite.exit_code == 3
    assert "Traceback" not in disconnected.stderr + bad_suite.stderr


def test_run_and_history_are_fully_offline(monkeypatch):
    monkeypatch.setattr("tessera.runner._default_eval", _writing_eval(True))

    result = RUNNER.invoke(app, ["run", "--model", "ollama/test", "--k", "1"])
    history = RUNNER.invoke(app, ["history", "--json"])

    assert result.exit_code == 0
    assert "Reliable. Right every time on all 1 question." in result.stdout
    assert "saved" in result.stdout
    payload = _json(history)
    assert history.exit_code == 0
    assert payload["runs"][0]["source"] == "run"
    assert payload["runs"][0]["id"] in result.stdout


def test_failed_gate_prints_one_run_payload(monkeypatch):
    monkeypatch.setattr("tessera.runner._default_eval", _writing_eval(False))

    result = RUNNER.invoke(
        app,
        [
            "run",
            "--model",
            "ollama/test",
            "--k",
            "1",
            "--min-pass-k",
            "1.0",
            "--json",
        ],
    )

    payload = _json(result)
    assert result.exit_code == 1
    assert payload["status"] == "completed" and payload["gate"]["passed"] is False


def test_archive_restore_and_bundled_rejection():
    store = RunStore(Path(os.environ["TESSERA_HOME"]))
    run_id = store.create(_spec()).id

    archived = RUNNER.invoke(app, ["archive", run_id])
    restored = RUNNER.invoke(app, ["archive", run_id, "--restore"])
    bundled = RUNNER.invoke(app, ["archive", "first-contact"])

    assert archived.exit_code == 0 and archived.stdout.strip() == f"archived {run_id}"
    assert restored.exit_code == 0 and restored.stdout.strip() == f"restored {run_id}"
    assert bundled.exit_code == 3


def test_import_adds_completed_run_to_history():
    imported = RUNNER.invoke(app, ["import", str(BUNDLED_LOG), "--json"])
    payload = _json(imported)
    history = RUNNER.invoke(app, ["history"])

    assert imported.exit_code == 0 and payload["status"] == "completed"
    assert payload["id"] in history.stdout


def test_catalog_json_and_provider_human_output():
    encoded = RUNNER.invoke(app, ["catalog", "--json"])
    providers_result = RUNNER.invoke(app, ["catalog", "providers"])

    payload = _json(encoded)
    assert encoded.exit_code == 0
    assert [suite["name"] for suite in payload["suites"][:2]] == ["starter", "meridian"]
    assert "anthropic  Anthropic  not connected" in providers_result.stdout


def test_connect_stdin_saves_without_disclosing_key():
    secret = "sk-test-secret-123"
    result = RUNNER.invoke(
        app,
        ["connect", "anthropic", "--key-stdin"],
        input=secret + "\n",
    )
    env_file = Path(os.environ["TESSERA_HOME"]) / ".env"
    catalog_result = RUNNER.invoke(app, ["catalog", "providers"])

    assert result.exit_code == 0
    assert env_file.exists() and stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert "ANTHROPIC_API_KEY=" in env_file.read_text(encoding="utf-8")
    assert secret not in result.stdout + result.stderr
    assert "anthropic  Anthropic  connected" in catalog_result.stdout


def test_connect_rejects_control_characters():
    result = RUNNER.invoke(
        app,
        ["connect", "anthropic", "--key-stdin"],
        input="sk-test-\x00bad\n",
    )

    assert result.exit_code == 3
    assert "error:" in result.stderr and "Traceback" not in result.stderr


def test_connect_probe_success_is_non_secret_and_non_networked(monkeypatch):
    monkeypatch.setattr(
        "tessera.providers.probe",
        lambda model: {
            "model": model,
            "ok": True,
            "latency_seconds": 1.2,
            "error": None,
        },
    )

    result = RUNNER.invoke(
        app,
        ["connect", "anthropic", "--key-stdin", "--test", "ollama/test"],
        input="sk-test-probe-123\n",
    )

    assert result.exit_code == 0
    assert "✓ probe ok: ollama/test answered in 1.2 s" in result.stdout


def test_compare_json_and_require_comparable_exit():
    encoded = RUNNER.invoke(app, ["compare", "first-contact", "gpt-4o", "--json"])
    payload = _json(encoded)
    required = RUNNER.invoke(
        app,
        ["compare", "first-contact", "gpt-4o", "--require-comparable"],
    )

    assert encoded.exit_code == 0 and payload["ok"] is True
    assert isinstance(payload["comparable"], bool)
    assert required.exit_code == (0 if payload["comparable"] else 1)


def test_unexpected_exception_is_redacted_without_a_traceback(monkeypatch):
    def fail(_self, *, include_archived=False):
        raise RuntimeError("boom")

    monkeypatch.setattr(RunStore, "list", fail)
    result = RUNNER.invoke(app, ["history"])

    assert result.exit_code == 4
    assert result.stderr.startswith("error: RuntimeError: boom")
    assert "Traceback" not in result.stdout + result.stderr
