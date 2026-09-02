from pathlib import Path

from fastapi.testclient import TestClient

from tessera.api.app import create_app
from tessera.api.run_store import RunStore
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
