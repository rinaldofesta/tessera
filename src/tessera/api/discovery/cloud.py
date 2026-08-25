"""Curated cloud catalogs with optional live provider confirmation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import httpx

from tessera.api.discovery.http import HttpClient
from tessera.api.discovery.models import DiscoveredModel, ModelReadiness, SourceResult

CREDENTIAL_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "xai": "XAI_API_KEY",
    "grok": "XAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

# These are deliberately the cloud models behind Tessera's published benchmark rows,
# not an attempt to mirror every provider's fast-moving catalog.
CLOUD_CATALOG = {
    "anthropic": (
        "claude-sonnet-4-6",
        "claude-opus-4-8",
        "claude-haiku-4-5",
    ),
    "openai": (
        "gpt-4o",
        "gpt-4o-mini",
    ),
}

_ENDPOINTS = {
    "anthropic": "https://api.anthropic.com/v1/models",
    "openai": "https://api.openai.com/v1/models",
}


def _catalog_models(
    provider: str,
    readiness: ModelReadiness,
    detail: str | None,
    *,
    only: set[str] | None = None,
    additional: Sequence[str] = (),
    include_catalog: bool = True,
) -> tuple[DiscoveredModel, ...]:
    candidates = (
        (*CLOUD_CATALOG[provider], *additional)
        if include_catalog
        else tuple(additional)
    )
    return tuple(
        DiscoveredModel(
            id=f"{provider}/{model}",
            label=model,
            provider=provider,
            readiness=readiness,
            detail=detail,
        )
        for model in dict.fromkeys(candidates)
        if only is None or model in only
    )


def _headers(provider: str, key: str) -> dict[str, str]:
    if provider == "anthropic":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    return {"authorization": f"Bearer {key}"}


def _model_ids(payload: object) -> set[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("provider returned an invalid models payload")
    return {
        row["id"]
        for row in payload["data"]
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }


def discover_cloud(
    client: HttpClient,
    environ: Mapping[str, str],
    *,
    timeout: float,
    additional: Mapping[str, Sequence[str]] | None = None,
    include_catalog: bool = True,
) -> tuple[SourceResult, ...]:
    """Return one independent result per curated cloud provider."""
    results: list[SourceResult] = []
    extra = additional or {}
    for provider in CLOUD_CATALOG:
        source = f"cloud:{provider}"
        env_name = CREDENTIAL_ENV[provider]
        key = environ.get(env_name, "").strip()
        if not key:
            results.append(SourceResult(
                source=source,
                status="needs_key",
                models=_catalog_models(
                    provider,
                    "needs_key",
                    f"Set {env_name}",
                    additional=extra.get(provider, ()),
                    include_catalog=include_catalog,
                ),
                detail=f"Set {env_name} to verify availability",
            ))
            continue

        try:
            response = client.get(
                _ENDPOINTS[provider],
                headers=_headers(provider, key),
                timeout=timeout,
            )
            response.raise_for_status()
            available = _model_ids(response.json())
        except httpx.TimeoutException:
            results.append(SourceResult(
                source=source,
                status="offline",
                models=_catalog_models(
                    provider,
                    "unverified",
                    "Provider timed out; availability unverified",
                    additional=extra.get(provider, ()),
                    include_catalog=include_catalog,
                ),
                detail="Provider model discovery timed out; using the curated catalog",
            ))
        except Exception:  # noqa: BLE001 — discovery degradation must never break setup
            results.append(SourceResult(
                source=source,
                status="degraded",
                models=_catalog_models(
                    provider,
                    "unverified",
                    "Provider unavailable; availability unverified",
                    additional=extra.get(provider, ()),
                    include_catalog=include_catalog,
                ),
                detail="Provider model discovery failed; using the curated catalog",
            ))
        else:
            results.append(SourceResult(
                source=source,
                status="ready",
                models=_catalog_models(
                    provider,
                    "ready",
                    None,
                    only=available,
                    additional=extra.get(provider, ()),
                    include_catalog=include_catalog,
                ),
                detail=f"Verified with {env_name}",
            ))
    return tuple(results)
