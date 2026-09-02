from pathlib import Path

from fastapi.testclient import TestClient

from tessera.api.app import create_app


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(
        home=tmp_path / "home",
        blueprint_dir=tmp_path / "bp",
        env_file=tmp_path / ".env",
    ))


def _done_run(client: TestClient) -> str:
    store = client.app.state.runs
    record = store.create({
        "suite": "starter", "model": "ollama/test", "engine": "deterministic",
        "grader": None, "k": 1, "scaffold": "baseline", "seed": 0,
    })
    store.mark_failed(record.id, "finished")
    return record.id


def test_archiving_a_done_run_hides_it_from_the_default_listing(tmp_path):
    client = _client(tmp_path)
    job_id = _done_run(client)

    archived = client.post(f"/api/runs/{job_id}/archive")

    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert job_id not in [row["id"] for row in client.get("/api/runs").json()]
    included = client.get("/api/runs?include_archived=true")
    archived_row = next(row for row in included.json() if row["id"] == job_id)
    assert archived_row["archived"] is True


def test_unarchiving_restores_a_run_to_the_default_listing(tmp_path):
    client = _client(tmp_path)
    job_id = _done_run(client)
    client.post(f"/api/runs/{job_id}/archive")

    restored = client.post(f"/api/runs/{job_id}/archive", json={"archived": False})

    assert restored.status_code == 200
    assert restored.json()["archived"] is False
    assert job_id in [row["id"] for row in client.get("/api/runs").json()]


def test_archiving_a_queued_run_is_allowed(tmp_path):
    client = _client(tmp_path)
    job_id = client.app.state.runs.create({
        "suite": "starter", "model": "ollama/test", "engine": "deterministic",
        "grader": None, "k": 1, "scaffold": "baseline", "seed": 0,
    }).id

    response = client.post(f"/api/runs/{job_id}/archive")

    assert response.status_code == 200
    assert response.json()["archived"] is True


def test_archiving_a_running_run_is_rejected(tmp_path):
    client = _client(tmp_path)
    store = client.app.state.runs
    record = store.create({
        "suite": "starter", "model": "ollama/test", "engine": "deterministic",
        "grader": None, "k": 1, "scaffold": "baseline", "seed": 0,
    })
    store.mark_running(record.id)

    response = client.post(f"/api/runs/{record.id}/archive")

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
    row = next(item for item in response.json() if item["id"] not in {"first-contact", "gpt-4o"})
    assert row["archived"] is False
