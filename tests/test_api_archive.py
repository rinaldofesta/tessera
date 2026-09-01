from pathlib import Path

from fastapi.testclient import TestClient

from tessera.api.app import create_app
from tessera.api.run_store import RunStore
from tessera.api.schemas import RunRequest


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(
        eval_runner=lambda req: None,
        log_dirs={"logs": tmp_path / "logs"},
        blueprint_dir=tmp_path / "bp",
        run_store=RunStore(tmp_path / "runs.db"),
        env_file=tmp_path / ".env",
    ))


def _done_run(client: TestClient) -> str:
    store = client.app.state.run_store
    job_id = store.create(RunRequest(model="test/model", judge="deterministic"))
    store.complete(job_id, {"overall": {"pass_k_rate": 1.0, "mean_rate": 1.0}})
    return job_id


def test_archiving_a_done_run_hides_it_from_the_default_listing(tmp_path):
    client = _client(tmp_path)
    job_id = _done_run(client)

    archived = client.post(f"/api/runs/{job_id}/archive")

    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert [row["id"] for row in client.get("/api/runs").json()] == []
    included = client.get("/api/runs?include_archived=true")
    assert [row["id"] for row in included.json()] == [job_id]
    assert included.json()[0]["archived"] is True


def test_unarchiving_restores_a_run_to_the_default_listing(tmp_path):
    client = _client(tmp_path)
    job_id = _done_run(client)
    client.post(f"/api/runs/{job_id}/archive")

    restored = client.post(f"/api/runs/{job_id}/archive", json={"archived": False})

    assert restored.status_code == 200
    assert restored.json()["archived"] is False
    assert [row["id"] for row in client.get("/api/runs").json()] == [job_id]


def test_archiving_a_running_run_is_rejected(tmp_path):
    client = _client(tmp_path)
    job_id = client.app.state.run_store.create(
        RunRequest(model="test/model", judge="deterministic"))

    response = client.post(f"/api/runs/{job_id}/archive")

    assert response.status_code == 409
    assert response.json()["detail"] == "a running evaluation cannot be archived"


def test_archiving_an_unknown_run_is_not_found(tmp_path):
    response = _client(tmp_path).post("/api/runs/unknown/archive")

    assert response.status_code == 404


def test_run_summaries_include_archived_false_by_default(tmp_path):
    client = _client(tmp_path)
    _done_run(client)

    response = client.get("/api/runs")

    assert response.status_code == 200
    assert response.json()[0]["archived"] is False


def test_archived_done_run_is_absent_from_trends(tmp_path):
    client = _client(tmp_path)
    job_id = _done_run(client)
    client.post(f"/api/runs/{job_id}/archive")

    assert client.get("/api/trends").json() == []
