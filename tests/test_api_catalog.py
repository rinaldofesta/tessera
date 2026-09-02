from __future__ import annotations

from fastapi.testclient import TestClient

from tessera.api.app import create_app
from tessera.api.run_store import RunStore


def _client(tmp_path) -> TestClient:
    return TestClient(create_app(
        home=tmp_path / "home",
        eval_runner=lambda req: None,
        log_dirs={"logs": tmp_path / "logs"},
        blueprint_dir=tmp_path / "suites",
        run_store=RunStore(tmp_path / "runs.db"),
        env_file=tmp_path / ".env",
    ))


def test_catalog_lists_canonical_builtins_without_secrets(tmp_path, monkeypatch):
    secret = "sk-S3NT1NEL-S3NT1NEL-S3NT1NEL"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)

    response = _client(tmp_path).get("/api/catalog")

    assert response.status_code == 200
    assert [suite["name"] for suite in response.json()["suites"]] == [
        "starter", "meridian",
    ]
    assert secret not in response.text


def test_dry_run_route_is_registered_before_dynamic_run_route(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    response = _client(tmp_path).post(
        "/api/runs/dry-run", json={"model": "anthropic/claude-sonnet-4-6"},
    )

    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_dry_run_returns_not_ready_plan(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    response = _client(tmp_path).post(
        "/api/runs/dry-run", json={"model": "anthropic/claude-sonnet-4-6"},
    )

    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert response.json()["blockers"][0]["fix"] == "tessera connect anthropic"


def test_dry_run_surfaces_missing_grader_as_a_blocker(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    response = _client(tmp_path).post(
        "/api/runs/dry-run",
        json={"model": "anthropic/claude-sonnet-4-6", "engine": "llm"},
    )

    assert response.status_code == 200
    assert [blocker["code"] for blocker in response.json()["blockers"]] == [
        "grader_required",
    ]


def test_old_vocabulary_routes_remain_available(tmp_path):
    client = _client(tmp_path)

    assert client.get("/api/eval-setup").status_code == 200
    assert client.get("/api/orgs").status_code == 200
