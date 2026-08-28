"""Cloud source: a curated catalog, confirmed by a live listing when a key exists.

Hybrid on purpose. A raw provider listing would drag embeddings and image models into
an eval dropdown; a pure catalog would go stale and would claim models this key cannot
reach. The catalog bounds what may appear; the live call decides what is `ready`.
"""

from __future__ import annotations

from collections.abc import Mapping

from tessera.api.providers import PROVIDERS, is_configured

from .types import DiscoveredModel, SourceResult

# Tool-capable chat models only. Adding a model here is a deliberate, reviewable act.
CATALOG: dict[str, tuple[str, ...]] = {
    "anthropic": (
        "anthropic/claude-opus-4-8",
        "anthropic/claude-sonnet-4-6",
        "anthropic/claude-haiku-4-5",
    ),
    "openai": ("openai/gpt-4o", "openai/gpt-4o-mini"),
    "openrouter": ("openrouter/meta-llama/llama-4-maverick",),
    "google": ("google/gemini-2.5-pro",),
    "groq": ("groq/llama-3.3-70b-versatile",),
    "mistral": ("mistral/mistral-large-latest",),
    "xai": ("xai/grok-3",),
}

_LIST_URL: dict[str, str] = {
    "anthropic": "https://api.anthropic.com/v1/models",
    "openai": "https://api.openai.com/v1/models",
    "openrouter": "https://openrouter.ai/api/v1/models",
}


def _auth_headers(provider_id: str, env: Mapping[str, str]) -> dict[str, str]:
    """The provider's own auth scheme. Without these the listing 401s and every model
    stays `unverified` — the live confirmation the hybrid design depends on can never
    succeed. Anthropic uses x-api-key plus a version header; the others use Bearer."""
    key = env.get(PROVIDERS[provider_id].fields[0].env_var, "").strip()
    if provider_id == "anthropic":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    return {"Authorization": f"Bearer {key}"}


def _reachable(client, provider_id: str, env: Mapping[str, str], timeout: float) -> set[str] | None:
    """Ids the key can reach, or None when no listing was obtained."""
    url = _LIST_URL.get(provider_id)
    if not url:
        return None
    try:
        response = client.get(url, timeout=timeout, headers=_auth_headers(provider_id, env))
        if getattr(response, "status_code", 200) != 200:
            return None
        payload = response.json()
    except Exception:  # noqa: BLE001 — degrade to the catalog, never empty the list
        return None
    entries = payload.get("data") if isinstance(payload, dict) else None
    return {e["id"] for e in (entries or []) if isinstance(e, dict) and e.get("id")}


def discover_cloud(client, *, env: Mapping[str, str], timeout: float = 4.0) -> SourceResult:
    models: list[DiscoveredModel] = []
    for provider_id, catalog in CATALOG.items():
        spec = PROVIDERS[provider_id]
        configured = is_configured(spec, env)
        reachable = _reachable(client, provider_id, env, timeout) if configured else None

        for model_id in catalog:
            _, _, label = model_id.rpartition("/")
            if not configured:
                readiness = "needs_config"
            elif reachable is None:
                readiness = "unverified"          # key present, listing unavailable
            else:
                bare = model_id.split("/", 1)[1]
                readiness = "ready" if (model_id in reachable or bare in reachable) else "unverified"
            models.append(DiscoveredModel(
                id=model_id, label=label, provider=provider_id,
                readiness=readiness, source="cloud",
            ))
    return SourceResult("cloud", tuple(models), "ok")
