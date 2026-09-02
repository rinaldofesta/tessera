from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from inspect_ai.log import write_eval_log

from tessera.runner import execute
from tessera.store import RunStore


def _spec(**overrides) -> dict:
    spec = {
        "suite": "starter",
        "model": "ollama/test",
        "engine": "deterministic",
        "grader": None,
        "k": 1,
        "scaffold": "baseline",
        "seed": 0,
    }
    spec.update(overrides)
    return spec


def _fake_log(location: str):
    from test_serialize import _answer, _eval_log

    log = _eval_log(
        [_answer("q1", 1, "none", True)],
        judge="deterministic",
        epochs=1,
        grader=None,
        model="ollama/test",
        location=location,
    )
    log.eval.task_args.update({
        "org": "toy", "k": 1, "scaffold": "baseline", "seed": 0,
    })
    return log


def _writing_eval(**kwargs):
    location = str(Path(kwargs["log_dir"]) / "inspect-output.eval")
    log = _fake_log(location)
    write_eval_log(log, location)
    return log


def test_execute_completes_into_run_folder_and_restores_environment(tmp_path):
    from tessera.report.serialize import report_to_dict

    store = RunStore(tmp_path / "home", examples=tmp_path / "examples")
    record = store.create(_spec())
    env = {"TESSERA_OUT": "before", "TESSERA_BLUEPRINT_DIR": "suites-before"}
    captured = {}

    def runner(**kwargs):
        captured["log"] = _writing_eval(**kwargs)
        return captured["log"]

    result = execute(
        record, _spec(), store=store, suites_dir=tmp_path / "suites",
        eval_fn=runner, env=env,
    )

    run_dir = Path(record.dir)
    assert result["status"] == "completed" and result["ok"] is True, result["error"]
    assert result["report"] == report_to_dict(captured["log"])
    assert env == {"TESSERA_OUT": "before", "TESSERA_BLUEPRINT_DIR": "suites-before"}
    assert {"log.eval", "report.json", "receipt.json", "report.md", "run.json"} <= {
        path.name for path in run_dir.iterdir()
    }
    assert not (run_dir / "inspect-output.eval").exists()
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert state["status"] == "completed" and state["owner"] is None


def test_execute_failure_is_scrubbed_and_returned(tmp_path, monkeypatch):
    store = RunStore(tmp_path / "home", examples=tmp_path / "examples")
    record = store.create(_spec())
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-key")

    def fail(**_kwargs):
        raise RuntimeError("provider rejected super-secret-key")

    result = execute(
        record, _spec(), store=store, suites_dir=tmp_path / "suites", eval_fn=fail,
    )

    assert result["status"] == "failed" and result["ok"] is False
    assert "[redacted]" in result["error"] and "super-secret-key" not in result["error"]


def test_execute_not_ready_fails_without_calling_eval(tmp_path):
    store = RunStore(tmp_path / "home", examples=tmp_path / "examples")
    record = store.create(_spec(suite="missing"))
    called = False

    def fail_if_called(**_kwargs):
        nonlocal called
        called = True

    result = execute(
        record, _spec(suite="missing"), store=store, suites_dir=tmp_path / "suites",
        eval_fn=fail_if_called,
    )

    assert called is False
    assert result["status"] == "failed" and "unknown suite" in result["error"]


def test_execute_serializes_process_global_eval_environment(tmp_path):
    store = RunStore(tmp_path / "home", examples=tmp_path / "examples")
    records = [store.create(_spec()), store.create(_spec())]
    active = False
    overlapped = False
    state_lock = threading.Lock()

    def guarded_eval(**kwargs):
        nonlocal active, overlapped
        with state_lock:
            if active:
                overlapped = True
            active = True
        time.sleep(0.05)
        log = _writing_eval(**kwargs)
        with state_lock:
            active = False
        return log

    threads = [
        threading.Thread(
            target=execute,
            args=(record, _spec()),
            kwargs={
                "store": store,
                "suites_dir": tmp_path / "suites",
                "eval_fn": guarded_eval,
                "env": {},
            },
        )
        for record in records
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert overlapped is False
    assert [store.get(record.id).data["status"] for record in records] == [
        "completed", "completed",
    ]
