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


def test_listing_providers_reports_names_and_booleans_only(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", SENTINEL)
    r = _client(tmp_path).get("/api/providers")
    assert r.status_code == 200
    assert SENTINEL not in r.text
    openai = next(p for p in r.json() if p["id"] == "openai")
    assert openai["fields"][0] == {"id": "api_key", "env_var": "OPENAI_API_KEY", "configured": True}


def test_a_multi_field_provider_reports_each_requirement_separately(tmp_path, monkeypatch):
    monkeypatch.delenv("MLX_API_KEY", raising=False)
    monkeypatch.setenv("MLX_BASE_URL", "http://localhost:8080/v1")
    mlx = next(p for p in _client(tmp_path).get("/api/providers").json() if p["id"] == "mlx")
    assert mlx["configured"] is False
    assert {f["id"]: f["configured"] for f in mlx["fields"]} == {"api_key": False, "base_url": True}


def test_writing_a_key_persists_it_and_reports_configured_without_echoing(tmp_path):
    client = _client(tmp_path)
    r = client.put("/api/providers/openai", json={"api_key": SENTINEL})
    assert r.status_code == 200
    assert SENTINEL not in r.text
    assert r.json()["configured"] is True
    assert SENTINEL in (tmp_path / ".env").read_text()      # it really was written


def test_writing_never_claims_a_readiness_it_did_not_observe(tmp_path):
    body = _client(tmp_path).put("/api/providers/openai", json={"api_key": SENTINEL}).json()
    assert body["readiness"] != "ready"


def test_an_unknown_provider_is_404_and_echoes_nothing(tmp_path):
    r = _client(tmp_path).put("/api/providers/nonesuch", json={"api_key": SENTINEL})
    assert r.status_code == 404
    assert SENTINEL not in r.text


def test_a_field_the_provider_does_not_have_is_rejected(tmp_path):
    # Assert on the file's bytes, not on a substring: the variable that would be written
    # is OPENAI_BASE_URL, so a lowercase "base_url" search can never fire and the test
    # would pass even if a regression wrote the rejected field.
    env = tmp_path / ".env"
    env.write_text("EXISTING=1\n")
    before = env.read_bytes()
    r = _client(tmp_path).put("/api/providers/openai", json={"base_url": "http://localhost:1/v1"})
    assert r.status_code == 422
    assert env.read_bytes() == before


def test_a_value_containing_a_newline_is_rejected_and_writes_nothing(tmp_path):
    env = tmp_path / ".env"
    env.write_text("EXISTING=1\n")
    before = env.read_text()
    r = _client(tmp_path).put("/api/providers/openai", json={"api_key": f"{SENTINEL}\nINJECTED=1"})
    assert r.status_code == 422
    assert SENTINEL not in r.text
    assert env.read_text() == before                        # byte-identical


def test_a_url_embedding_credentials_is_rejected_without_echoing_it(tmp_path):
    r = _client(tmp_path).put(
        "/api/providers/mlx", json={"base_url": f"http://user:{SENTINEL}@host/v1"})
    assert r.status_code == 422
    assert SENTINEL not in r.text


def test_the_credential_scanner_finds_nothing_in_any_response(tmp_path):
    client = _client(tmp_path)
    client.put("/api/providers/openai", json={"api_key": SENTINEL})
    for path in ("/api/providers", "/api/eval-setup", "/api/runs", "/api/models"):
        response = client.get(path)
        assert SENTINEL not in response.text, path
        assert find_credential_like_values(response.json()) == [], path


def test_rescan_reports_each_source_status(tmp_path):
    body = _client(tmp_path).post("/api/model-discovery/rescan").json()
    assert {s["source"] for s in body["sources"]} == {"cloud", "ollama", "mlx"}


def test_a_typo_in_a_field_name_is_rejected_rather_than_silently_ignored(tmp_path):
    # pydantic's default drops unknown members, so {"apikey": ...} returned 200 having
    # written nothing — the caller walks away believing the credential is stored.
    env = tmp_path / ".env"
    env.write_text("EXISTING=1\n")
    before = env.read_bytes()
    r = _client(tmp_path).put("/api/providers/openai", json={"apikey": SENTINEL})
    assert r.status_code == 422
    assert SENTINEL not in r.text
    assert env.read_bytes() == before
