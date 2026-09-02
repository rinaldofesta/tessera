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
from tessera.cli import api_alias, app, leaderboard_alias, report_alias
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


def test_ui_check_reports_checkout_bundle(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    bundle = checkout / "web" / "dist" / "index.html"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("<main>Tessera</main>")
    monkeypatch.setattr("tessera.__file__", str(checkout / "src" / "tessera" / "__init__.py"))
    monkeypatch.setattr("tessera.api.app.resources.files", lambda _package: tmp_path / "package")

    result = RUNNER.invoke(app, ["ui", "--check"])

    assert result.exit_code == 0
    assert f"ui bundle: {bundle}" in result.stdout
    assert "api: ok" in result.stdout


def test_ui_check_missing_bundle_json_shape(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    monkeypatch.setattr("tessera.__file__", str(checkout / "src" / "tessera" / "__init__.py"))
    monkeypatch.setattr("tessera.api.app.resources.files", lambda _package: tmp_path / "package")

    result = RUNNER.invoke(app, ["ui", "--check", "--json"])

    payload = _json(result)
    assert result.exit_code == 0
    assert payload == {
        "ok": True,
        "api": "ok",
        "ui_bundle": None,
        "home": os.environ["TESSERA_HOME"],
        "env_file": str(Path(os.environ["TESSERA_HOME"]) / ".env"),
        "env_file_present": False,
    }


def test_ui_launch_uses_env_port_and_schedules_browser(monkeypatch):
    uvicorn_calls = []
    timers = []

    class FakeTimer:
        def __init__(self, interval, function, args):
            self.interval = interval
            self.function = function
            self.args = args
            self.daemon = False
            self.started = False
            timers.append(self)

        def start(self):
            self.started = True

    monkeypatch.setenv("TESSERA_API_PORT", "8124")
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: uvicorn_calls.append((args, kwargs)))
    monkeypatch.setattr("tessera.cli.threading.Timer", FakeTimer)

    result = RUNNER.invoke(app, ["ui"])

    assert result.exit_code == 0 and "http://127.0.0.1:8124" in result.stdout
    assert uvicorn_calls[0][1] == {
        "factory": True,
        "host": "127.0.0.1",
        "port": 8124,
        "log_level": "warning",
    }
    assert timers[0].interval == 1.0 and timers[0].args == ("http://127.0.0.1:8124",)
    assert timers[0].daemon is True and timers[0].started is True


def test_guide_every_topic_loads_and_agents_is_real():
    from tessera.guide import text, topics

    assert [topic["name"] for topic in topics()] == [
        "start",
        "conflicts",
        "suites",
        "reading",
        "agents",
    ]
    assert all(text(topic["name"]).strip() for topic in topics())
    agents = RUNNER.invoke(app, ["guide", "agents"])
    assert agents.exit_code == 0 and "tessera run" in agents.stdout


def test_guide_list_json_and_unknown_topic():
    listed = RUNNER.invoke(app, ["guide", "--list", "--json"])
    payload = _json(listed)
    unknown = RUNNER.invoke(app, ["guide", "unknown"])

    assert listed.exit_code == 0
    assert [topic["name"] for topic in payload["topics"]] == [
        "start",
        "conflicts",
        "suites",
        "reading",
        "agents",
    ]
    assert unknown.exit_code == 3


def test_guide_defaults_to_start_in_json():
    result = RUNNER.invoke(app, ["guide", "--json"])

    payload = _json(result)
    assert result.exit_code == 0 and payload["topic"] == "start"
    assert "tessera report first-contact" in payload["text"]


def test_guide_human_list_has_exactly_five_topic_lines():
    result = RUNNER.invoke(app, ["guide", "--list"])

    assert result.exit_code == 0
    assert [line.split(" — ", 1)[0] for line in result.stdout.splitlines()] == [
        "start",
        "conflicts",
        "suites",
        "reading",
        "agents",
    ]


def test_init_validate_and_custom_suite_dry_run():
    initialized = RUNNER.invoke(app, ["init", "demo", "--json"])
    init_payload = _json(initialized)
    path = Path(init_payload["path"])
    validated = RUNNER.invoke(app, ["validate", "demo"])
    builtin = RUNNER.invoke(app, ["validate", "starter"])
    planned = RUNNER.invoke(
        app,
        ["run", "--model", "ollama/test", "--suite", "demo", "--dry-run", "--json"],
    )

    assert initialized.exit_code == 0 and path.is_file()
    assert path.read_text().endswith("\n") and '\n  "claims": [' in path.read_text()
    assert validated.exit_code == 0 and "ok: demo" in validated.stdout
    assert builtin.exit_code == 0 and "ok: starter" in builtin.stdout
    assert _json(planned)["suite"]["name"] == "demo"


def test_init_refuses_overwrite_builtin_and_bad_name():
    first = RUNNER.invoke(app, ["init", "demo"])
    overwrite = RUNNER.invoke(app, ["init", "demo"])
    builtin = RUNNER.invoke(app, ["init", "starter"])
    bad_name = RUNNER.invoke(app, ["init", "../demo"])

    assert first.exit_code == 0
    assert overwrite.exit_code == builtin.exit_code == bad_name.exit_code == 3


@pytest.mark.parametrize("reserved", ["starter", "meridian", "toy"])
def test_init_refuses_every_builtin_name_and_alias(reserved):
    result = RUNNER.invoke(app, ["init", reserved])

    assert result.exit_code == 3 and "reserved" in result.stderr


def test_validate_broken_file_has_located_issue_and_one_json_envelope(tmp_path):
    initialized = RUNNER.invoke(app, ["init", "demo", "--json"])
    data = json.loads(Path(_json(initialized)["path"]).read_text())
    del data["claims"][0]["subject"]
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(data))

    human = RUNNER.invoke(app, ["validate", str(broken)])
    encoded = RUNNER.invoke(app, ["validate", str(broken), "--json"])
    payload = _json(encoded)

    assert human.exit_code == encoded.exit_code == 3
    assert "claims.0.subject:" in human.stdout
    assert payload["ok"] is False
    assert payload["issues"][0]["location"] == "claims.0.subject"


def test_validate_malformed_json_prints_validation_envelope(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text('{"claims": [')

    result = RUNNER.invoke(app, ["validate", str(broken), "--json"])

    payload = _json(result)
    assert result.exit_code == 3 and payload["ok"] is False
    assert payload["issues"][0]["location"].startswith("line 1 column")


def test_validate_invalid_saved_suite_by_name_reports_its_issue():
    initialized = RUNNER.invoke(app, ["init", "demo", "--json"])
    path = Path(_json(initialized)["path"])
    data = json.loads(path.read_text())
    del data["probes"][0]["question"]
    path.write_text(json.dumps(data))

    result = RUNNER.invoke(app, ["validate", "demo"])

    assert result.exit_code == 3 and "probes.0.question:" in result.stdout


def test_leaderboard_render_matches_committed_markdown_and_verify_passes():
    repo = Path(__file__).parents[1]
    manifest = repo / "docs" / "leaderboard.rows.json"

    rendered = RUNNER.invoke(app, ["leaderboard", "render", "--manifest", str(manifest)])
    verified = RUNNER.invoke(app, ["leaderboard", "verify", "--manifest", str(manifest)])

    assert rendered.exit_code == 0
    assert rendered.stdout == (repo / "docs" / "leaderboard.md").read_text()
    assert verified.exit_code == 0 and verified.stdout.startswith("verified ")


def test_leaderboard_render_title_override():
    repo = Path(__file__).parents[1]
    result = RUNNER.invoke(
        app,
        [
            "leaderboard",
            "render",
            "--manifest",
            str(repo / "docs" / "leaderboard.rows.json"),
            "--title",
            "# Custom leaderboard",
        ],
    )

    assert result.exit_code == 0 and result.stdout.startswith("# Custom leaderboard\n")


def test_leaderboard_extract_wraps_existing_log_machinery():
    result = RUNNER.invoke(
        app, ["leaderboard", "extract", str(BUNDLED_LOG), "--label", "first-contact"],
    )

    (row,) = json.loads(result.stdout)
    assert result.exit_code == 0 and row["label"] == "first-contact"
    assert row["log"]["path"] == "src/tessera/data/examples/first-contact/log.eval"


def test_leaderboard_verify_missing_manifest_preserves_legacy_exit(tmp_path):
    result = RUNNER.invoke(
        app,
        ["leaderboard", "verify", "--manifest", str(tmp_path / "missing.json")],
    )

    assert result.exit_code == 2 and "cannot read manifest:" in result.stderr


def test_report_alias_deprecates_and_delegates(tmp_path):
    out = tmp_path / "scorecard.md"
    result = RUNNER.invoke(report_alias, ["first-contact", "-o", str(out)])

    assert result.exit_code == 0 and "75%" in out.read_text()
    assert result.stderr == "tessera-report is deprecated — use: tessera report …\n"


def test_report_alias_delegates_to_stdout_without_out():
    result = RUNNER.invoke(report_alias, ["first-contact"])

    assert result.exit_code == 0 and "75%" in result.stdout
    assert result.stderr == "tessera-report is deprecated — use: tessera report …\n"


def test_leaderboard_alias_deprecates_and_delegates():
    repo = Path(__file__).parents[1]
    result = RUNNER.invoke(
        leaderboard_alias,
        ["--manifest", str(repo / "docs" / "leaderboard.rows.json")],
    )

    assert result.exit_code == 0
    assert result.stdout == (repo / "docs" / "leaderboard.md").read_text()
    assert result.stderr.startswith("tessera-leaderboard is deprecated — use:")


def test_leaderboard_alias_translates_extract_and_forwards_options():
    result = RUNNER.invoke(
        leaderboard_alias,
        ["--extract", str(BUNDLED_LOG), "--label", "first-contact"],
    )

    (row,) = json.loads(result.stdout)
    assert result.exit_code == 0 and row["label"] == "first-contact"


def test_leaderboard_alias_renders_logs_and_forwards_positional_options():
    result = RUNNER.invoke(
        leaderboard_alias,
        [str(BUNDLED_LOG), "--label", "first-contact"],
    )

    # This bundled log predates the required scorer-version field, so the renderer's
    # comparability guard rejects it. Reaching that guard proves the positional log and
    # label survived alias translation (a Click routing failure would print usage).
    assert result.exit_code == 2
    assert "rows are not comparable" in result.stderr


def test_api_alias_deprecates_and_delegates(monkeypatch):
    called = {}
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: called.update(kwargs))

    result = RUNNER.invoke(api_alias, ["--port", "8123"])

    assert result.exit_code == 0 and called["port"] == 8123
    assert called["host"] == "127.0.0.1"
    assert result.stderr == "tessera-api is deprecated — use: tessera ui --no-open\n"


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
