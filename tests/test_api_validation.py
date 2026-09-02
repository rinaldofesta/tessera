from pathlib import Path
from typing import get_args

from fastapi.testclient import TestClient

from tessera.api.app import create_app
from tessera.api.run_store import RunStore
from tessera.api.schemas import RunRequest
from tessera.credential_scan import find_credential_like_values

SENTINEL = "sk-" + "S3NT1NEL" * 4


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(
        eval_runner=lambda req: None,
        log_dirs={"logs": tmp_path / "logs"},
        blueprint_dir=tmp_path / "bp",
        run_store=RunStore(tmp_path / "runs.db"),
        env_file=tmp_path / ".env",
    ))


def test_a_validation_error_does_not_echo_the_rejected_value(tmp_path):
    # FastAPI's default handler returns pydantic's `input` field verbatim.
    r = _client(tmp_path).post("/api/runs", json={"model": {"nested": SENTINEL}, "org": "toy"})
    assert r.status_code == 422
    assert SENTINEL not in r.text


def test_a_validation_error_still_says_which_field_and_why(tmp_path):
    r = _client(tmp_path).post("/api/runs", json={"model": {"nested": "x"}, "org": "toy"})
    detail = r.json()["detail"][0]
    assert detail["loc"] == ["body", "model"]
    assert detail["msg"]
    assert "input" not in detail and "ctx" not in detail


def test_the_credential_scanner_finds_nothing_in_a_validation_error(tmp_path):
    r = _client(tmp_path).post("/api/runs", json={"model": {"nested": SENTINEL}, "org": "toy"})
    assert find_credential_like_values(r.json()) == []


def test_existing_closed_enum_validation_still_returns_422(tmp_path):
    r = _client(tmp_path).post("/api/runs", json={"model": "m", "judge": "nonesuch", "org": "toy"})
    assert r.status_code == 422


def test_llm_judge_requires_a_grader(tmp_path):
    r = _client(tmp_path).post("/api/runs", json={"model": "m", "judge": "llm"})
    assert r.status_code == 422
    assert r.json()["detail"][0]["msg"] == "Value error, grader is required when judge is 'llm'"


def test_deterministic_judge_rejects_a_grader(tmp_path):
    r = _client(tmp_path).post(
        "/api/runs", json={"model": "m", "judge": "deterministic", "grader": "g"},
    )
    assert r.status_code == 422
    assert r.json()["detail"][0]["msg"] == "Value error, grader only applies to judge 'llm'"


def test_a_model_only_request_uses_deterministic_defaults(tmp_path):
    assert _client(tmp_path).post("/api/runs", json={"model": "m"}).status_code == 200
    request = RunRequest(model="m")
    assert (request.judge, request.org, request.epochs, request.scaffold, request.seed) == (
        "deterministic", "toy", 3, "baseline", 0,
    )


def test_run_request_scaffolds_are_supported_by_the_task():
    from tessera.evals.task import _SCAFFOLDS

    annotation = RunRequest.model_fields["scaffold"].annotation
    assert set(get_args(annotation)) <= set(_SCAFFOLDS)
