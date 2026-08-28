import pytest

from tessera.api.discovery.ollama import discover_ollama


class _StubClient:
    """Minimal stand-in for httpx.Client — the suite is network-free by design."""

    def __init__(self, *, payload=None, status_code=200, raises=None):
        self.payload, self.status_code, self.raises = payload, status_code, raises
        self.calls: list[str] = []
        self.headers: list[dict] = []

    def get(self, url, timeout=None, headers=None):
        self.calls.append(url)
        self.headers.append(headers or {})
        if self.raises is not None:
            raise self.raises
        return self

    def json(self):
        return self.payload


def test_ollama_lists_installed_models_as_ready():
    client = _StubClient(payload={"models": [{"name": "qwen3:4b"}, {"name": "llama3:8b"}]})
    result = discover_ollama(client)
    assert result.status == "ok"
    assert [m.id for m in result.models] == ["ollama/qwen3:4b", "ollama/llama3:8b"]
    assert {m.readiness for m in result.models} == {"ready"}
    assert client.calls == ["http://localhost:11434/api/tags"]


def test_a_daemon_that_refuses_the_connection_is_offline_with_no_models():
    result = discover_ollama(_StubClient(raises=OSError("connection refused")))
    assert (result.status, result.models) == ("offline", ())
    assert result.detail is not None


def test_the_offline_detail_never_leaks_the_exception_text():
    # Exception strings can carry URLs, and a URL can carry credentials.
    secret = "http://user:sk-SENTINEL-123@host/v1"
    result = discover_ollama(_StubClient(raises=OSError(secret)))
    assert "sk-SENTINEL-123" not in (result.detail or "")


def test_a_non_200_response_is_offline_rather_than_an_empty_success():
    result = discover_ollama(_StubClient(status_code=503, payload={}))
    assert result.status == "offline"


def test_a_malformed_payload_yields_no_models_without_raising():
    result = discover_ollama(_StubClient(payload={"unexpected": True}))
    assert (result.status, result.models) == ("ok", ())


from pathlib import Path

from tessera.api.discovery.mlx import discover_mlx


def _hf_cache(tmp_path: Path, *repos: str) -> Path:
    hub = tmp_path / "hub"
    for repo in repos:
        (hub / repo).mkdir(parents=True)
    return tmp_path


def test_mlx_repos_on_disk_with_no_server_are_needs_server_with_the_serve_command():
    import tempfile
    root = _hf_cache(Path(tempfile.mkdtemp()), "models--mlx-community--Qwen3-4bit")
    result = discover_mlx(_StubClient(raises=OSError()), hf_home=root, base_url=None)
    assert result.status == "ok"
    assert [m.id for m in result.models] == ["openai-api/mlx/mlx-community/Qwen3-4bit"]
    assert result.models[0].readiness == "needs_server"
    assert "mlx_lm.server" in (result.models[0].detail or "")


def test_a_served_model_is_ready_and_outranks_its_on_disk_row():
    import tempfile
    root = _hf_cache(Path(tempfile.mkdtemp()), "models--mlx-community--Qwen3-4bit")
    client = _StubClient(payload={"data": [{"id": "mlx-community/Qwen3-4bit"}]})
    result = discover_mlx(client, hf_home=root, base_url="http://localhost:8080/v1")
    ready = [m for m in result.models if m.readiness == "ready"]
    assert [m.id for m in ready] == ["openai-api/mlx/mlx-community/Qwen3-4bit"]
    assert len(result.models) == 1  # not duplicated by the disk scan


def test_non_mlx_repos_in_the_cache_are_ignored():
    import tempfile
    root = _hf_cache(Path(tempfile.mkdtemp()), "models--openai--whisper", "models--mlx-community--A")
    result = discover_mlx(_StubClient(raises=OSError()), hf_home=root, base_url=None)
    assert [m.id for m in result.models] == ["openai-api/mlx/mlx-community/A"]


def test_a_missing_cache_directory_is_an_empty_success_not_a_crash():
    result = discover_mlx(_StubClient(raises=OSError()), hf_home=Path("/nonexistent"), base_url=None)
    assert (result.status, result.models) == ("ok", ())


def test_a_served_id_differing_only_in_case_does_not_duplicate_the_disk_row():
    # The served id comes from the server, the disk name from a cache directory. When
    # they differ only in case they are the same model, and two rows with contradictory
    # readiness (ready + needs_server) would be actively misleading.
    import tempfile
    root = _hf_cache(Path(tempfile.mkdtemp()), "models--mlx-community--Qwen3-4bit")
    client = _StubClient(payload={"data": [{"id": "MLX-Community/Qwen3-4bit"}]})
    result = discover_mlx(client, hf_home=root, base_url="http://localhost:8080/v1")
    assert len(result.models) == 1
    assert result.models[0].readiness == "ready"


from tessera.api.discovery.cloud import CATALOG, discover_cloud


def test_a_provider_with_no_key_is_needs_config_and_is_never_probed():
    client = _StubClient(payload={"data": []})
    result = discover_cloud(client, env={})
    assert result.status == "ok"
    assert {m.readiness for m in result.models} == {"needs_config"}
    assert client.calls == []            # no key, no request


def test_catalog_models_confirmed_by_a_live_listing_are_ready():
    listed = [{"id": model} for model in CATALOG["openai"]]
    client = _StubClient(payload={"data": listed})
    result = discover_cloud(client, env={"OPENAI_API_KEY": "sk-x"})
    openai_models = [m for m in result.models if m.provider == "openai"]
    assert openai_models and {m.readiness for m in openai_models} == {"ready"}


def test_a_listing_that_omits_a_catalog_model_leaves_it_unverified_not_ready():
    client = _StubClient(payload={"data": [{"id": "some-other-model"}]})
    result = discover_cloud(client, env={"OPENAI_API_KEY": "sk-x"})
    openai_models = [m for m in result.models if m.provider == "openai"]
    assert {m.readiness for m in openai_models} == {"unverified"}


def test_a_failed_listing_degrades_to_the_catalog_rather_than_emptying_the_list():
    result = discover_cloud(_StubClient(raises=OSError("boom")), env={"OPENAI_API_KEY": "sk-x"})
    openai_models = [m for m in result.models if m.provider == "openai"]
    assert len(openai_models) == len(CATALOG["openai"])
    assert {m.readiness for m in openai_models} == {"unverified"}


def test_models_outside_the_catalog_never_enter_the_dropdown():
    # A provider listing includes embeddings and image models; none may reach an eval.
    client = _StubClient(payload={"data": [{"id": "text-embedding-3-large"}]})
    result = discover_cloud(client, env={"OPENAI_API_KEY": "sk-x"})
    assert all("embedding" not in m.id for m in result.models)


def test_no_response_field_can_carry_the_key_back():
    from tessera.credential_scan import find_credential_like_values
    result = discover_cloud(_StubClient(payload={"data": []}), env={"OPENAI_API_KEY": "sk-" + "a" * 32})
    payload = [m.__dict__ for m in result.models] + [{"detail": result.detail}]
    assert find_credential_like_values(payload) == []


def test_the_cloud_listing_is_sent_with_the_provider_credential():
    # Without auth headers the listing 401s, _reachable returns None, and every model
    # stays `unverified` — the live confirmation the hybrid design exists for could
    # never succeed. The key must never appear in the RESULT, only in the request.
    client = _StubClient(payload={"data": []})
    discover_cloud(client, env={"OPENAI_API_KEY": "sk-token", "ANTHROPIC_API_KEY": "sk-ant"})
    sent = {url: h for url, h in zip(client.calls, client.headers)}
    assert sent["https://api.openai.com/v1/models"]["Authorization"] == "Bearer sk-token"
    anthropic = sent["https://api.anthropic.com/v1/models"]
    assert anthropic["x-api-key"] == "sk-ant"
    assert anthropic["anthropic-version"]


def test_no_auth_header_is_sent_for_a_provider_without_a_key():
    client = _StubClient(payload={"data": []})
    discover_cloud(client, env={"OPENAI_API_KEY": "sk-token"})
    assert "https://api.anthropic.com/v1/models" not in client.calls
