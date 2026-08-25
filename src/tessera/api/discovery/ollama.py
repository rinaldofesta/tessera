"""Live Ollama model discovery."""

from __future__ import annotations

import httpx

from tessera.api.discovery.http import HttpClient
from tessera.api.discovery.models import DiscoveredModel, SourceResult


def discover_ollama(
    client: HttpClient,
    *,
    base_url: str,
    timeout: float,
) -> SourceResult:
    try:
        response = client.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            raise ValueError("Ollama returned an invalid tags payload")
        names = sorted({
            row["name"]
            for row in payload["models"]
            if isinstance(row, dict) and isinstance(row.get("name"), str)
        })
    except httpx.TimeoutException:
        return SourceResult(
            source="ollama",
            status="offline",
            detail="Ollama model discovery timed out",
        )
    except httpx.ConnectError:
        return SourceResult(
            source="ollama",
            status="unreachable",
            detail="Ollama is not reachable",
        )
    except Exception:  # noqa: BLE001 — malformed/down runtimes degrade, never raise
        return SourceResult(
            source="ollama",
            status="unreachable",
            detail="Ollama model discovery failed",
        )
    return SourceResult(
        source="ollama",
        status="ready",
        models=tuple(
            DiscoveredModel(
                id=f"ollama/{name}",
                label=name,
                provider="ollama",
                readiness="ready",
            )
            for name in names
        ),
        detail=f"Found {len(names)} installed model{'s' if len(names) != 1 else ''}",
    )
