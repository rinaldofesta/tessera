from __future__ import annotations

from tessera.contract import Run
from tessera.runner import run_result_payload
from tessera.store import RunStore


def _first_contact_record(tmp_path):
    return RunStore(tmp_path).get("first-contact")


def _run_request() -> dict:
    return {
        "suite": "meridian",
        "model": "mock/model",
        "engine": "deterministic",
        "grader": None,
        "k": 3,
        "scaffold": "baseline",
        "seed": 0,
    }


def test_completed_bundled_run_has_operational_ok_and_data_derived_verdict(tmp_path):
    payload = run_result_payload(_first_contact_record(tmp_path))

    assert payload["ok"] is True
    assert payload["verdict"]["label"] == "unreliable"
    assert payload["verdict"]["pass_k_rate"] == 0.75
    assert payload["gate"] is None


def test_failed_gate_does_not_change_operational_ok(tmp_path):
    payload = run_result_payload(_first_contact_record(tmp_path), min_pass_k=1.0)

    assert payload["gate"] == {"min_pass_k": 1.0, "passed": False}
    assert payload["ok"] is True


def test_inconsistent_verdict_uses_mean_above_pass_k(tmp_path):
    record = RunStore(tmp_path).get("gpt-4o")

    assert run_result_payload(record)["verdict"]["label"] == "inconsistent"


def test_failed_run_is_not_ok_and_has_no_verdict(tmp_path):
    store = RunStore(tmp_path)
    failed = store.mark_failed(store.create(_run_request()).id, "provider failed")

    payload = run_result_payload(failed)

    assert payload["ok"] is False
    assert payload["verdict"] is None
    assert payload["error"] == "provider failed"


def test_payload_round_trips_through_contract(tmp_path):
    payload = run_result_payload(_first_contact_record(tmp_path), min_pass_k=1.0)

    assert Run.model_validate(payload).model_dump() == payload
