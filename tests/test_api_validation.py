from pathlib import Path

from fastapi.testclient import TestClient

from tessera.api.app import create_app
from tessera.api.run_store import RunStore
from tessera.api.schemas import RunRequest
from tessera.credential_scan import find_credential_like_values

SENTINEL = "sk-" + "S3NT1NEL" * 4


async def _inline_schedule(coro):
    await coro


def _no_eval(**_kwargs):
    raise AssertionError("validation tests never execute a run")


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(
        home=tmp_path / "home",
        eval_runner=lambda req: None,
        folder_eval_runner=_no_eval,
        schedule=_inline_schedule,
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
    r = _client(tmp_path).post("/api/runs", json={"model": "ollama/test", "engine": "llm"})
    assert r.status_code == 422
    assert r.json()["detail"][0]["message"] == "grader is required when engine is 'llm'"


def test_deterministic_judge_rejects_a_grader(tmp_path):
    r = _client(tmp_path).post(
        "/api/runs", json={
            "model": "ollama/test", "engine": "deterministic", "grader": "ollama/grader",
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"][0]["message"] == "grader only applies to engine 'llm'"


def test_a_model_only_request_uses_deterministic_defaults(tmp_path):
    from tessera.contract import RunSpec

    assert _client(tmp_path).post("/api/runs", json={"model": "ollama/test"}).status_code == 200
    request = RunSpec(model="ollama/test")
    assert (request.engine, request.suite, request.k, request.scaffold, request.seed) == (
        "deterministic", "starter", 3, "baseline", 0,
    )


def test_run_request_scaffolds_are_supported_by_the_task():
    from tessera.evals.task import _SCAFFOLDS

    assert RunRequest.model_fields["scaffold"].default in _SCAFFOLDS
