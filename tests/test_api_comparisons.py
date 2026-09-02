from fastapi.testclient import TestClient

from tessera.api.app import create_app


def _client(tmp_path):
    return TestClient(create_app(
        home=tmp_path / "home",
        blueprint_dir=tmp_path / "suites",
        env_file=tmp_path / ".env",
    ))


def test_compare_bundled_runs(tmp_path):
    response = _client(tmp_path).post(
        "/api/comparisons",
        json={"a": "first-contact", "b": "gpt-4o"},
    )

    assert response.status_code == 200
    assert isinstance(response.json()["compatible"], bool)
    assert isinstance(response.json()["overall"]["p_value"], float)


def test_compare_unknown_run_is_not_found(tmp_path):
    response = _client(tmp_path).post(
        "/api/comparisons",
        json={"a": "missing", "b": "gpt-4o"},
    )

    assert response.status_code == 404


def test_compare_queued_run_conflicts(tmp_path):
    client = _client(tmp_path)
    queued = client.app.state.runs.create({
        "suite": "starter",
        "model": "ollama/test",
        "engine": "deterministic",
        "grader": None,
        "k": 1,
        "scaffold": "baseline",
        "seed": 0,
    })

    response = client.post(
        "/api/comparisons",
        json={"a": queued.id, "b": "gpt-4o"},
    )

    assert response.status_code == 409
