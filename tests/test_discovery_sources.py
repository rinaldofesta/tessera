import pytest

from tessera.api.discovery.ollama import discover_ollama


class _StubClient:
    """Minimal stand-in for httpx.Client — the suite is network-free by design."""

    def __init__(self, *, payload=None, status_code=200, raises=None):
        self.payload, self.status_code, self.raises = payload, status_code, raises
        self.calls: list[str] = []

    def get(self, url, timeout=None):
        self.calls.append(url)
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
