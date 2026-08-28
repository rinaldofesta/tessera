"""Cloud source: filtered live listings, with a curated fallback for outages."""

from __future__ import annotations

import re
from collections.abc import Mapping

from tessera.api.providers import PROVIDERS, is_configured

from .types import DiscoveredModel, SourceResult

# Fallback only: a successful live listing is authoritative for what this key can reach.
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

# A filter, not an allowlist: the catalogue could never show a model nobody typed in. The cost
# is that this is a denylist of shapes, so a genuinely new non-chat model type could slip
# through until this learns it — accepted deliberately, see the phase-3 design note.
_NON_CHAT = re.compile(
    r"(?i)embed|whisper|tts|dall-?e|moderation|transcrib|realtime|audio|image|sora"
    r"|rerank|guard|codex|search|computer-use"
)
_LEGACY_COMPLETION = re.compile(r"(?i)^(babbage|davinci|curie|ada)-")
# Pinned snapshots duplicate an alias that is already listed; keeping both doubles the picker.
_DATED_SNAPSHOT = re.compile(r"-\d{4}-\d{2}-\d{2}$|-\d{6,8}$")


def is_chat_model(model_id: str) -> bool:
    """Whether a listed model can plausibly be evaluated as a chat/tool model."""
    return not (
        _NON_CHAT.search(model_id)
        or _LEGACY_COMPLETION.search(model_id)
        or _DATED_SNAPSHOT.search(model_id)
    )


_LIST_URL: dict[str, str] = {
    "anthropic": "https://api.anthropic.com/v1/models",
    "openai": "https://api.openai.com/v1/models",
    "openrouter": "https://openrouter.ai/api/v1/models",
}


def _auth_headers(provider_id: str, env: Mapping[str, str]) -> dict[str, str]:
    """The provider's own auth scheme. Without these the listing 401s and discovery
    falls back to `unverified`. Anthropic uses x-api-key plus a version header; the
    others use Bearer."""
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
        if not is_configured(spec, env):
            continue

        reachable = _reachable(client, provider_id, env, timeout)
        if reachable is None:
            candidates = ((model_id, "unverified") for model_id in catalog)
        else:
            candidates = (
                (f"{provider_id}/{bare}", "ready")
                for bare in sorted(reachable)
                if is_chat_model(bare)
            )

        for model_id, readiness in candidates:
            _, _, label = model_id.rpartition("/")
            models.append(DiscoveredModel(
                id=model_id, label=label, provider=provider_id,
                readiness=readiness, source="cloud",
            ))
    return SourceResult("cloud", tuple(models), "ok")
