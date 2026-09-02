from __future__ import annotations

import json
import re
import socket
from datetime import datetime
from pathlib import Path

import psutil
import pytest

import tessera.store as store_module
from tessera.errors import SpecError
from tessera.store import RunStore, _write_atomic


def _request() -> dict:
    return {
        "suite": "meridian",
        "model": "mock/model",
        "engine": "deterministic",
        "grader": None,
        "k": 3,
        "scaffold": "baseline",
        "seed": 0,
    }


def _bundled_run(root: Path, run_id: str) -> Path:
    directory = root / run_id
    directory.mkdir(parents=True)
    data = {
        "schema_version": 1,
        "id": run_id,
        "status": "completed",
        "source": "bundled",
        "archived": False,
        "created_at": "2026-01-01T00:00:00+00:00",
        "started_at": None,
        "finished_at": "2026-01-01T00:00:00+00:00",
        "request": _request(),
        "owner": None,
        "error": None,
    }
    (directory / "run.json").write_text(json.dumps(data), encoding="utf-8")
    return directory


def test_create_id_shape_and_utc_timestamp(tmp_path):
    record = RunStore(tmp_path).create(_request())

    assert re.fullmatch(r"\d{8}-\d{6}-[a-z2-7]{8}", record.id)
    created = datetime.fromisoformat(record.data["created_at"])
    assert created.utcoffset().total_seconds() == 0
    assert record.data["status"] == "queued"


def test_create_retries_an_id_collision(tmp_path, monkeypatch):
    values = iter([b"same!", b"same!", b"other"])
    monkeypatch.setattr(store_module.secrets, "token_bytes", lambda _n: next(values))
    store = RunStore(tmp_path)

    first = store.create(_request())
    second = store.create(_request())

    assert first.id != second.id
    assert first.dir.is_dir() and second.dir.is_dir()


def test_atomic_write_leaves_original_intact_when_replace_fails(tmp_path, monkeypatch):
    path = tmp_path / "run.json"
    _write_atomic(path, b"original")

    def fail_replace(_source, _destination):
        raise OSError("replace failed")

    monkeypatch.setattr(store_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        _write_atomic(path, b"replacement")

    assert path.read_bytes() == b"original"
    assert not (tmp_path / "run.json.tmp").exists()


def test_completion_writes_artifacts_before_completed_state(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    record = store.create(_request())
    original_write_state = store._write_state

    def assert_artifacts_first(directory, data):
        if data["status"] == "completed":
            assert (directory / "report.json").is_file()
            assert (directory / "receipt.json").is_file()
            assert (directory / "report.md").is_file()
        original_write_state(directory, data)

    monkeypatch.setattr(store, "_write_state", assert_artifacts_first)
    completed = store.mark_completed(
        record.id,
        report={"overall": {}},
        receipt={"protocol_hash": "x"},
        markdown="# report\n",
        log_path=None,
    )

    assert completed.data["status"] == "completed"


def test_mark_running_records_process_owner(tmp_path):
    store = RunStore(tmp_path)
    running = store.mark_running(store.create(_request()).id)

    assert running.data["owner"] == {
        "pid": store_module.os.getpid(),
        "hostname": socket.gethostname(),
        "process_started_at": psutil.Process().create_time(),
    }
    assert datetime.fromisoformat(running.data["started_at"]).utcoffset().total_seconds() == 0


def test_reconcile_interrupts_a_run_when_pid_is_gone(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    running = store.mark_running(store.create(_request()).id)

    def missing_process(pid=None):
        raise psutil.NoSuchProcess(pid or -1)

    monkeypatch.setattr(store_module.psutil, "Process", missing_process)

    assert store.reconcile() == [running.id]
    assert store.get(running.id).data["status"] == "interrupted"


def test_reconcile_interrupts_reused_pid_with_different_create_time(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    running = store.mark_running(store.create(_request()).id)
    recorded = running.data["owner"]["process_started_at"]

    class ReusedProcess:
        def __init__(self, _pid=None):
            pass

        def create_time(self):
            return recorded + 2.0

    monkeypatch.setattr(store_module.psutil, "Process", ReusedProcess)

    assert store.reconcile() == [running.id]


def test_reconcile_leaves_owner_on_another_hostname(tmp_path):
    store = RunStore(tmp_path)
    running = store.mark_running(store.create(_request()).id)
    state_path = Path(running.dir) / "run.json"
    state = json.loads(state_path.read_text())
    state["owner"]["hostname"] = "another-host"
    _write_atomic(state_path, store_module._json_bytes(state))

    assert store.reconcile() == []
    assert store.get(running.id).data["status"] == "running"


def test_reconcile_interrupts_running_state_without_owner(tmp_path):
    store = RunStore(tmp_path)
    record = store.create(_request())
    state_path = Path(record.dir) / "run.json"
    state = json.loads(state_path.read_text())
    state["status"] = "running"
    _write_atomic(state_path, store_module._json_bytes(state))

    assert store.reconcile() == [record.id]
    assert store.get(record.id).data["status"] == "interrupted"


def test_bundled_aliases_resolve_list_and_are_read_only(tmp_path):
    examples = tmp_path / "bundled"
    _bundled_run(examples, "first-contact")
    _bundled_run(examples, "gpt-4o")
    store = RunStore(tmp_path / "home", examples)

    assert store.get("first-contact").data["source"] == "bundled"
    assert [record.id for record in store.list()] == ["first-contact", "gpt-4o"]
    with pytest.raises(SpecError, match="bundled example runs are read-only"):
        store.set_archived("first-contact", True)


def test_default_bundled_examples_are_listed_without_home_state(tmp_path):
    assert [record.id for record in RunStore(tmp_path).list()] == ["first-contact", "gpt-4o"]


def test_bundled_alias_resolves_before_a_home_shadow(tmp_path):
    _bundled_run(tmp_path / "runs", "first-contact")
    store = RunStore(tmp_path)

    assert store.get("first-contact").dir != tmp_path / "runs" / "first-contact"


def test_list_skips_folder_without_readable_state_and_records_diagnostic(tmp_path):
    corrupt = tmp_path / "runs" / "corrupt"
    corrupt.mkdir(parents=True)
    store = RunStore(tmp_path)

    assert "corrupt" not in [record.id for record in store.list()]
    assert len(store.diagnostics) == 1 and "corrupt" in store.diagnostics[0]


def test_archive_round_trip(tmp_path):
    store = RunStore(tmp_path)
    run_id = store.create(_request()).id

    assert store.set_archived(run_id, True).data["archived"] is True
    assert run_id not in [record.id for record in store.list()]
    assert store.set_archived(run_id, False).data["archived"] is False
    assert [record.id for record in store.list()][0] == run_id


def test_import_log_builds_a_completed_run(tmp_path):
    log_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "tessera" / "data" / "examples" / "first-contact" / "log.eval"
    )

    record = RunStore(tmp_path).import_log(log_path)

    assert record.data["status"] == "completed"
    assert record.report()["overall"]["pass_k_rate"] == 0.75
    assert (Path(record.dir) / "log.eval").read_bytes() == log_path.read_bytes()


def test_import_log_refuses_a_bundled_alias(tmp_path):
    log_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "tessera" / "data" / "examples" / "first-contact" / "log.eval"
    )

    with pytest.raises(SpecError, match="reserved by a bundled example"):
        RunStore(tmp_path).import_log(log_path, id="first-contact")


def test_higher_schema_version_is_rejected(tmp_path):
    store = RunStore(tmp_path)
    record = store.create(_request())
    state_path = Path(record.dir) / "run.json"
    state = json.loads(state_path.read_text())
    state["schema_version"] = 2
    _write_atomic(state_path, store_module._json_bytes(state))

    with pytest.raises(SpecError, match=r"schema version 2.*supported version 1"):
        store.get(record.id)


# ----- fix wave after the adversarial review -----


def test_transition_rereads_state_so_a_concurrent_archive_is_not_lost(tmp_path):
    store = RunStore(tmp_path)
    run_id = store.create(_request()).id
    store.mark_running(run_id)
    # Another process archives the run between our read and our completion write.
    RunStore(tmp_path).set_archived(run_id, True)

    record = store.mark_completed(
        run_id, report={"overall": {}}, receipt={}, markdown="# r", log_path=None,
    )

    assert record.data["status"] == "completed" and record.data["archived"] is True


def test_reconcile_never_downgrades_a_run_that_completed_meanwhile(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    run_id = store.create(_request()).id
    store.mark_running(run_id)
    listed = store._list_root  # the scan sees "running"; completion lands before the lock
    def scan(root, *, bundled):
        records = listed(root, bundled=bundled)
        store.mark_completed(
            run_id, report={"overall": {}}, receipt={}, markdown="# r", log_path=None,
        )
        return records
    monkeypatch.setattr(store, "_list_root", scan)
    monkeypatch.setattr(store_module.psutil, "Process", lambda pid: (_ for _ in ()).throw(
        psutil.NoSuchProcess(pid)))

    assert store.reconcile() == []
    assert store.get(run_id).data["status"] == "completed"


def test_symlinked_run_folder_is_not_a_run(tmp_path):
    store = RunStore(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "run.json").write_text(json.dumps({
        "schema_version": 1, "id": "escape", "status": "queued", "source": "run",
        "archived": False, "created_at": "2026-01-01T00:00:00+00:00", "started_at": None,
        "finished_at": None, "request": _request(), "owner": None, "error": None,
    }))
    store._ensure_runs()
    (store.runs / "escape").symlink_to(outside, target_is_directory=True)

    with pytest.raises(SpecError, match="unknown run"):
        store.set_archived("escape", True)
    assert [record.id for record in store.list() if record.id == "escape"] == []
    assert json.loads((outside / "run.json").read_text())["archived"] is False


def test_reserved_ids_are_refused_even_without_an_examples_root(tmp_path):
    store = RunStore(tmp_path, examples=tmp_path / "no-examples-here")
    log_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "tessera" / "data" / "examples" / "first-contact" / "log.eval"
    )

    with pytest.raises(SpecError, match="reserved"):
        store.import_log(log_path, id="first-contact")
    (store.runs / "gpt-4o").mkdir(parents=True)
    (store.runs / "gpt-4o" / "run.json").write_text("{}")
    assert [record.id for record in store.list()] == []


def test_non_integer_schema_version_is_corrupt_not_a_newer_schema(tmp_path):
    store = RunStore(tmp_path)
    record = store.create(_request())
    state_path = Path(record.dir) / "run.json"
    state = json.loads(state_path.read_text())
    state["schema_version"] = "2"
    _write_atomic(state_path, store_module._json_bytes(state))

    assert record.id not in [r.id for r in store.list()] and store.diagnostics
    with pytest.raises(SpecError, match="unreadable"):
        store.get(record.id)


def test_atomic_write_uses_a_unique_temporary_name(tmp_path, monkeypatch):
    seen = []
    real_replace = store_module.os.replace
    def spy(src, dst):
        seen.append(Path(src).name)
        real_replace(src, dst)
    monkeypatch.setattr(store_module.os, "replace", spy)

    _write_atomic(tmp_path / "run.json", b"1")
    _write_atomic(tmp_path / "run.json", b"2")

    assert len(set(seen)) == 2 and all(name.startswith("run.json.") for name in seen)
    assert list(tmp_path.glob("*.tmp")) == []


# ----- fix wave after the xhigh code-review pass -----


def test_list_skips_a_newer_schema_run_instead_of_aborting_the_whole_listing(tmp_path):
    store = RunStore(tmp_path)
    ok = store.create(_request())
    newer = store.create(_request())
    state_path = Path(newer.dir) / "run.json"
    state = json.loads(state_path.read_text())
    state["schema_version"] = 2
    _write_atomic(state_path, store_module._json_bytes(state))

    listed = [record.id for record in store.list()]

    assert ok.id in listed and newer.id not in listed
    assert any("schema version 2" in d for d in store.diagnostics)
    with pytest.raises(SpecError, match=r"schema version 2.*supported version 1"):
        store.get(newer.id)


def test_create_rejects_a_source_outside_the_shared_contract(tmp_path):
    store = RunStore(tmp_path)

    with pytest.raises(SpecError, match="invalid run source"):
        store.create(_request(), source="typo-ed-source")

    assert not (tmp_path / "runs").exists()


def test_import_log_marks_the_run_failed_instead_of_leaving_it_queued_forever(tmp_path, monkeypatch):
    log_path = (
        Path(__file__).resolve().parents[1]
        / "src" / "tessera" / "data" / "examples" / "first-contact" / "log.eval"
    )
    store = RunStore(tmp_path)
    monkeypatch.setattr(
        store_module, "receipt_from_log",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="boom"):
        store.import_log(log_path)

    (run_dir,) = (tmp_path / "runs").iterdir()
    record = store.get(run_dir.name)
    assert record.data["status"] == "failed"
    assert record.data["error"] == "boom"


def test_reconcile_skips_a_run_that_becomes_unreadable_mid_sweep(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    running = store.mark_running(store.create(_request()).id)
    real_home_dir = store._home_dir
    calls = {"n": 0}

    def flaky_home_dir(ref):
        calls["n"] += 1
        # First call is _transition's own precondition check; force it to look like the
        # run vanished between reconcile()'s listing pass and the locked transition.
        return None if calls["n"] > 1 else real_home_dir(ref)

    monkeypatch.setattr(store, "_home_dir", flaky_home_dir)

    assert store.reconcile() == []
    assert any(running.id in d for d in store.diagnostics)


def test_failed_completion_leaves_no_partial_artifacts(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    run_id = store.create(_request()).id
    store.mark_running(run_id)
    real_write = store_module._write_atomic
    def fail_on_receipt(path, payload):
        if path.name == "receipt.json":
            raise OSError("disk full")
        real_write(path, payload)
    monkeypatch.setattr(store_module, "_write_atomic", fail_on_receipt)

    with pytest.raises(OSError, match="disk full"):
        store.mark_completed(run_id, report={"overall": {}}, receipt={}, markdown="# r", log_path=None)

    directory = Path(store.get(run_id).dir)
    assert not (directory / "report.json").exists() and not (directory / "report.md").exists()
    assert store.get(run_id).data["status"] == "running"
