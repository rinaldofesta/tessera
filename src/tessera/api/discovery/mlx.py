"""Discover MLX models from a live server and the Hugging Face cache."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from tessera.api.discovery.http import HttpClient
from tessera.api.discovery.models import DiscoveredModel, SourceResult


def _served_id(model_id: str) -> str:
    if model_id.startswith("openai-api/mlx/"):
        return model_id
    return f"openai-api/mlx/{model_id}"


def _scan_cache(cache_root: Path, port: int) -> dict[str, DiscoveredModel]:
    models: dict[str, DiscoveredModel] = {}
    if not cache_root.is_dir():
        return models
    for path in sorted(cache_root.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_dir() or not path.name.startswith("models--"):
            continue
        parts = path.name.removeprefix("models--").split("--", 1)
        if len(parts) != 2:
            continue
        org, name = parts
        if org.lower() != "mlx-community" and "mlx" not in name.lower():
            continue
        repo = f"{org}/{name}"
        model_id = _served_id(repo)
        models[model_id] = DiscoveredModel(
            id=model_id,
            label=repo,
            provider="mlx",
            readiness="needs_server",
            detail=f"mlx_lm.server --model {repo} --port {port}",
        )
    return models


def _server_models(payload: object) -> set[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("MLX server returned an invalid models payload")
    return {
        row["id"]
        for row in payload["data"]
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }


def discover_mlx(
    client: HttpClient,
    cache_root: Path,
    *,
    base_url: str,
    timeout: float,
) -> SourceResult:
    parsed = urlparse(base_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    cached = _scan_cache(cache_root, port)
    try:
        response = client.get(f"{base_url.rstrip('/')}/v1/models", timeout=timeout)
        response.raise_for_status()
        served = _server_models(response.json())
    except httpx.TimeoutException:
        return SourceResult(
            source="mlx",
            status="offline",
            models=tuple(cached.values()),
            detail="MLX server discovery timed out",
        )
    except httpx.ConnectError:
        return SourceResult(
            source="mlx",
            status="unreachable",
            models=tuple(cached.values()),
            detail="MLX server is not reachable",
        )
    except Exception:  # noqa: BLE001 — malformed/down runtimes degrade, never raise
        return SourceResult(
            source="mlx",
            status="unreachable",
            models=tuple(cached.values()),
            detail="MLX server discovery failed",
        )

    models = dict(cached)
    for raw_id in served:
        model_id = _served_id(raw_id)
        label = raw_id.removeprefix("openai-api/mlx/")
        models[model_id] = DiscoveredModel(
            id=model_id,
            label=label,
            provider="mlx",
            readiness="ready",
        )
    ordered = tuple(models[key] for key in sorted(models))
    return SourceResult(
        source="mlx",
        status="ready",
        models=ordered,
        detail=f"Found {len(served)} served model{'s' if len(served) != 1 else ''}",
    )
