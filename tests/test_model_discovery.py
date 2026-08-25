"""Offline unit tests for model discovery sources, merging, and caching."""

from __future__ import annotations

from pathlib import Path

import httpx

from tessera.api.discovery.cache import DiscoveryCache
from tessera.api.discovery.cloud import discover_cloud
from tessera.api.discovery.merge import benchmark_models, merge_models
from tessera.api.discovery.mlx import discover_mlx
from tessera.api.discovery.models import DiscoveredModel, DiscoverySnapshot, SourceResult
from tessera.api.discovery.ollama import discover_ollama
from tessera.api.discovery.service import create_default_cache, discover_snapshot


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.test/models")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("failed", request=request, response=response)

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, *, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        result = self.routes[url]
        if isinstance(result, Exception):
            raise result
        return result


def connect_error(url: str = "http://localhost") -> httpx.ConnectError:
    return httpx.ConnectError("down", request=httpx.Request("GET", url))


def timeout_error(url: str = "http://localhost") -> httpx.TimeoutException:
    return httpx.ReadTimeout("slow", request=httpx.Request("GET", url))


def test_cloud_without_keys_returns_catalog_without_http():
    client = FakeClient({})
    results = discover_cloud(client, {}, timeout=1.25)

    assert client.calls == []
    assert [result.status for result in results] == ["needs_key", "needs_key"]
    assert {model.readiness for result in results for model in result.models} == {"needs_key"}
    assert "ANTHROPIC_API_KEY" in results[0].detail


def test_cloud_confirms_available_catalog_models_and_degrades_safely():
    client = FakeClient({
        "https://api.anthropic.com/v1/models": FakeResponse({
            "data": [{"id": "claude-sonnet-4-6"}, {"id": "not-in-catalog"}],
        }),
        "https://api.openai.com/v1/models": timeout_error(),
    })
    results = discover_cloud(
        client,
        {"ANTHROPIC_API_KEY": "secret-a", "OPENAI_API_KEY": "secret-b"},
        timeout=0.75,
    )

    assert results[0].status == "ready"
    assert [model.id for model in results[0].models] == ["anthropic/claude-sonnet-4-6"]
    assert results[1].status == "offline"
    assert all(model.readiness == "unverified" for model in results[1].models)
    assert all(call["timeout"] == 0.75 for call in client.calls)
    assert client.calls[0]["headers"]["x-api-key"] == "secret-a"


def test_cloud_can_confirm_an_explicit_custom_model_without_expanding_catalog():
    client = FakeClient({
        "https://api.anthropic.com/v1/models": FakeResponse({
            "data": [{"id": "custom-sonnet"}, {"id": "unrequested-model"}],
        }),
    })
    results = discover_cloud(
        client,
        {"ANTHROPIC_API_KEY": "secret"},
        timeout=1,
        additional={"anthropic": ["custom-sonnet"]},
    )

    assert [model.id for model in results[0].models] == ["anthropic/custom-sonnet"]


def test_cloud_custom_model_without_key_keeps_needs_key_readiness():
    results = discover_cloud(
        FakeClient({}),
        {},
        timeout=1,
        additional={"anthropic": ["custom-sonnet"]},
        include_catalog=False,
    )

    assert [model.id for model in results[0].models] == ["anthropic/custom-sonnet"]
    assert results[0].models[0].readiness == "needs_key"


def test_ollama_reports_only_installed_models_and_handles_connection_refusal():
    url = "http://ollama.test/api/tags"
    live = discover_ollama(
        FakeClient({url: FakeResponse({"models": [{"name": "qwen3:4b"}]})}),
        base_url="http://ollama.test",
        timeout=1,
    )
    down = discover_ollama(
        FakeClient({url: connect_error(url)}),
        base_url="http://ollama.test",
        timeout=1,
    )

    assert live.status == "ready"
    assert [model.id for model in live.models] == ["ollama/qwen3:4b"]
    assert down.status == "unreachable" and down.models == ()


def test_ollama_timeout_is_offline():
    url = "http://ollama.test/api/tags"
    result = discover_ollama(
        FakeClient({url: timeout_error(url)}),
        base_url="http://ollama.test",
        timeout=0.25,
    )

    assert result.status == "offline" and result.models == ()


def test_mlx_combines_served_models_and_cache_with_ready_winning(tmp_path):
    (tmp_path / "models--mlx-community--Qwen3-4B-MLX").mkdir()
    (tmp_path / "models--someone--also-mlx-model").mkdir()
    (tmp_path / "models--someone--ordinary-model").mkdir()
    url = "http://mlx.test:8090/v1/models"
    result = discover_mlx(
        FakeClient({url: FakeResponse({
            "data": [
                {"id": "mlx-community/Qwen3-4B-MLX"},
                {"id": "org/served-only"},
            ],
        })}),
        tmp_path,
        base_url="http://mlx.test:8090",
        timeout=1,
    )
    by_id = {model.id: model for model in result.models}

    assert result.status == "ready"
    assert by_id["openai-api/mlx/mlx-community/Qwen3-4B-MLX"].readiness == "ready"
    assert by_id["openai-api/mlx/someone/also-mlx-model"].readiness == "needs_server"
    assert "--port 8090" in by_id["openai-api/mlx/someone/also-mlx-model"].detail
    assert "openai-api/mlx/someone/ordinary-model" not in by_id
    assert by_id["openai-api/mlx/org/served-only"].readiness == "ready"


def test_mlx_cached_model_needs_server_when_runtime_is_down(tmp_path):
    (tmp_path / "models--mlx-community--cached-model").mkdir()
    url = "http://mlx.test:8090/v1/models"
    result = discover_mlx(
        FakeClient({url: connect_error(url)}),
        tmp_path,
        base_url="http://mlx.test:8090",
        timeout=1,
    )

    assert result.status == "unreachable"
    assert result.models[0].readiness == "needs_server"


def test_mlx_timeout_is_offline_and_preserves_cached_models(tmp_path):
    (tmp_path / "models--mlx-community--cached-model").mkdir()
    url = "http://mlx.test:8090/v1/models"
    result = discover_mlx(
        FakeClient({url: timeout_error(url)}),
        tmp_path,
        base_url="http://mlx.test:8090",
        timeout=0.25,
    )

    assert result.status == "offline"
    assert result.models[0].readiness == "needs_server"


def test_merge_preserves_benchmark_group_and_stably_sorts_discovered():
    curated = benchmark_models({"TESSERA_MODELS": "ollama/qwen3:4b"})
    sources = (
        SourceResult("ollama", "ready", models=(
            DiscoveredModel("ollama/zeta", "zeta", "ollama", "ready"),
            DiscoveredModel("ollama/qwen3:4b", "qwen3:4b", "ollama", "ready"),
            DiscoveredModel("ollama/alpha", "alpha", "ollama", "ready"),
        )),
    )
    snapshot = merge_models(curated, sources)

    assert [model.id for model in snapshot.models] == [
        "ollama/qwen3:4b", "ollama/alpha", "ollama/zeta",
    ]
    assert snapshot.models[0].group == "benchmark"
    assert snapshot.models[0].readiness == "ready"
    assert all(model.group == "discovered" for model in snapshot.models[1:])


def test_whitespace_only_model_override_keeps_default_readiness():
    models = benchmark_models({"TESSERA_MODELS": " , ", "ANTHROPIC_API_KEY": ""})

    assert models[0].id == "anthropic/claude-sonnet-4-6"
    assert models[0].readiness == "needs_key"


def test_custom_override_replaces_catalog_and_is_deduplicated(tmp_path):
    routes = {
        "http://ollama.test/api/tags": connect_error("http://ollama.test/api/tags"),
        "http://mlx.test:8090/v1/models": connect_error(
            "http://mlx.test:8090/v1/models"
        ),
    }
    snapshot = discover_snapshot(
        FakeClient(routes),
        {
            "TESSERA_MODELS": "custom/model, custom/model",
            "OLLAMA_HOST": "ollama.test",
            "MLX_BASE_URL": "mlx.test:8090",
        },
        tmp_path,
        timeout=1,
    )

    assert [model.id for model in snapshot.models] == ["custom/model"]
    assert snapshot.models[0].readiness == "unverified"


def test_cache_reads_never_refresh_and_ttl_refreshes_once():
    initial = DiscoverySnapshot((), ())
    fresh = DiscoverySnapshot(
        (DiscoveredModel("ollama/x", "x", "ollama", "ready"),),
        (SourceResult("ollama", "ready"),),
    )
    now = [10.0]
    calls = []
    cache = DiscoveryCache(
        lambda: calls.append("refresh") or fresh,
        initial,
        ttl_seconds=5,
        clock=lambda: now[0],
    )

    assert cache.snapshot() is initial and calls == []
    assert cache.refresh_if_stale() is fresh and calls == ["refresh"]
    now[0] = 14.9
    assert cache.refresh_if_stale() is fresh and calls == ["refresh"]
    now[0] = 15.0
    assert cache.refresh_if_stale() is fresh and calls == ["refresh", "refresh"]


def test_default_cache_honors_ttl_timeout_and_runtime_url_overrides(
    tmp_path, monkeypatch
):
    import tessera.api.discovery.service as service

    ollama_url = "http://ollama.test:11435/api/tags"
    mlx_url = "http://mlx.test:8091/v1/models"
    fake_client = FakeClient({
        ollama_url: FakeResponse({"models": []}),
        mlx_url: FakeResponse({"data": []}),
    })
    constructed_with = []

    class ClientContext:
        def __init__(self, *, timeout):
            constructed_with.append(timeout)

        def __enter__(self):
            return fake_client

        def __exit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(service.httpx, "Client", ClientContext)
    cache = create_default_cache({
        "TESSERA_DISCOVERY_TTL": "12.5",
        "TESSERA_DISCOVERY_TIMEOUT": "0.25",
        "OLLAMA_HOST": "ollama.test:11435",
        "MLX_BASE_URL": "mlx.test:8091",
        "HF_HOME": str(tmp_path / "hf"),
    }, home=tmp_path)

    cache.refresh()

    assert cache.ttl_seconds == 12.5
    assert constructed_with == [0.25]
    assert [call["url"] for call in fake_client.calls] == [ollama_url, mlx_url]
    assert {call["timeout"] for call in fake_client.calls} == {0.25}
