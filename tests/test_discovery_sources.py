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
