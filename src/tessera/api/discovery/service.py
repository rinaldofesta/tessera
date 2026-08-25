"""Compose pure discovery sources into the default cached service."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

import httpx

from tessera.api.discovery.cache import DiscoveryCache
from tessera.api.discovery.cloud import CREDENTIAL_ENV, CLOUD_CATALOG, discover_cloud
from tessera.api.discovery.http import HttpClient
from tessera.api.discovery.merge import benchmark_models, merge_models
from tessera.api.discovery.mlx import discover_mlx
from tessera.api.discovery.models import DiscoverySnapshot, SourceResult
from tessera.api.discovery.ollama import discover_ollama

DEFAULT_TTL_SECONDS = 60.0
DEFAULT_TIMEOUT_SECONDS = 2.0


def _positive_float(raw: str | None, default: float) -> float:
    try:
        value = float(raw) if raw is not None else default
    except ValueError:
        return default
    return value if value > 0 else default


def _base_url(raw: str, default: str) -> str:
    value = raw.strip() or default
    return value if "://" in value else f"http://{value}"


def huggingface_cache_root(environ: Mapping[str, str], home: Path) -> Path:
    if explicit := environ.get("HUGGINGFACE_HUB_CACHE", "").strip():
        return Path(explicit)
    if hf_home := environ.get("HF_HOME", "").strip():
        return Path(hf_home) / "hub"
    return home / ".cache" / "huggingface" / "hub"


def initial_snapshot(environ: Mapping[str, str]) -> DiscoverySnapshot:
    sources: list[SourceResult] = []
    for provider in CLOUD_CATALOG:
        env_name = CREDENTIAL_ENV[provider]
        configured = bool(environ.get(env_name, "").strip())
        sources.append(SourceResult(
            source=f"cloud:{provider}",
            status="degraded" if configured else "needs_key",
            detail=(
                "Waiting for provider verification"
                if configured
                else f"Set {env_name} to verify availability"
            ),
        ))
    sources.extend((
        SourceResult("ollama", "offline", detail="Waiting for runtime discovery"),
        SourceResult("mlx", "offline", detail="Waiting for runtime discovery"),
    ))
    return DiscoverySnapshot(
        models=benchmark_models(environ),
        sources=tuple(sources),
    )


def discover_snapshot(
    client: HttpClient,
    environ: Mapping[str, str],
    home: Path,
    *,
    timeout: float,
) -> DiscoverySnapshot:
    additional: dict[str, list[str]] = {}
    custom_models = any(
        model.strip() for model in environ.get("TESSERA_MODELS", "").split(",")
    )
    if custom_models:
        for model_id in benchmark_models(environ):
            provider, separator, label = model_id.id.partition("/")
            if separator and provider in CLOUD_CATALOG:
                additional.setdefault(provider, []).append(label)
    results: list[SourceResult] = list(discover_cloud(
        client,
        environ,
        timeout=timeout,
        additional=additional,
        include_catalog=not custom_models,
    ))
    try:
        results.append(discover_ollama(
            client,
            base_url=_base_url(
                environ.get("OLLAMA_HOST", ""), "http://localhost:11434"
            ),
            timeout=timeout,
        ))
    except Exception:  # noqa: BLE001 — a source can never take down discovery
        results.append(SourceResult("ollama", "offline", detail="Ollama discovery failed"))
    try:
        results.append(discover_mlx(
            client,
            huggingface_cache_root(environ, home),
            base_url=_base_url(
                environ.get("MLX_BASE_URL", ""), "http://localhost:8090"
            ),
            timeout=timeout,
        ))
    except Exception:  # noqa: BLE001 — filesystem/runtime failures stay source-local
        results.append(SourceResult("mlx", "offline", detail="MLX discovery failed"))
    return merge_models(benchmark_models(environ), results)


def create_default_cache(
    environ: Mapping[str, str] | None = None,
    *,
    home: Path | None = None,
) -> DiscoveryCache:
    # Keep os.environ live: main() loads .env after importing the module-level app but
    # before startup, so the first background refresh must see those newly loaded keys.
    env = os.environ if environ is None else environ
    home_path = Path.home() if home is None else home
    ttl = _positive_float(env.get("TESSERA_DISCOVERY_TTL"), DEFAULT_TTL_SECONDS)
    timeout = _positive_float(
        env.get("TESSERA_DISCOVERY_TIMEOUT"), DEFAULT_TIMEOUT_SECONDS
    )

    def refresh() -> DiscoverySnapshot:
        with httpx.Client(timeout=timeout) as client:
            return discover_snapshot(client, env, home_path, timeout=timeout)

    return DiscoveryCache(
        refresh,
        initial_snapshot(env),
        ttl_seconds=ttl,
    )
