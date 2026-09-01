import json
from pathlib import Path

from fastapi.testclient import TestClient

from tessera.api.app import create_app
from tessera.api.run_store import RunStore


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(
        eval_runner=lambda req: None,
        log_dirs={"logs": tmp_path / "logs"},
        blueprint_dir=tmp_path / "bp",
        run_store=RunStore(tmp_path / "runs.db"),
        env_file=tmp_path / ".env",
    ))


def test_leaderboard_serves_the_committed_manifest_verbatim(tmp_path):
    response = _client(tmp_path).get("/api/leaderboard")
    expected = json.loads(Path("docs/leaderboard.rows.json").read_text())

    assert response.status_code == 200
    assert set(response.json()) == {"title", "rows", "exhibitions"}
    assert response.json()["rows"][0] == expected["rows"][0]


def test_leaderboard_returns_a_clear_404_when_the_manifest_is_missing(tmp_path, monkeypatch):
    from tessera.api import routes_meta

    monkeypatch.setattr(routes_meta, "_LEADERBOARD", tmp_path / "missing.json")
    response = _client(tmp_path).get("/api/leaderboard")

    assert response.status_code == 404
    assert response.json()["detail"] == "leaderboard manifest not found (docs/leaderboard.rows.json)"
