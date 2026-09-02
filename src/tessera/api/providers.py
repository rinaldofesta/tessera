"""Canonical provider registry.

A provider is the unit configuration is written to. It is deliberately NOT the same
thing as a model-string prefix: `xai/` and `grok/` are two prefixes that share one
credential, and `openai-api/mlx/...` is a prefix whose provider is the service name
that follows it. Keeping these separate is what lets one provider appear once in the
UI and one write target one variable.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

FIELD_API_KEY = "api_key"
FIELD_BASE_URL = "base_url"


@dataclass(frozen=True)
class ProviderField:
    id: str
    env_var: str
    required: bool


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    fields: tuple[ProviderField, ...]
    model_prefixes: tuple[str, ...]
    needs_credentials: bool


def _key_only(provider_id: str, env_var: str, *prefixes: str) -> ProviderSpec:
    return ProviderSpec(
        id=provider_id,
        fields=(ProviderField(FIELD_API_KEY, env_var, required=True),),
        model_prefixes=prefixes,
        needs_credentials=True,
    )


PROVIDERS: dict[str, ProviderSpec] = {
    "anthropic": _key_only("anthropic", "ANTHROPIC_API_KEY", "anthropic/"),
    "openai": _key_only("openai", "OPENAI_API_KEY", "openai/"),
    "openrouter": _key_only("openrouter", "OPENROUTER_API_KEY", "openrouter/"),
    "google": _key_only("google", "GOOGLE_API_KEY", "google/"),
    "groq": _key_only("groq", "GROQ_API_KEY", "groq/"),
    "mistral": _key_only("mistral", "MISTRAL_API_KEY", "mistral/"),
    # One provider, two prefixes: inspect_ai registers both `xai/` and `grok/`.
    "xai": _key_only("xai", "XAI_API_KEY", "xai/", "grok/"),
    # OpenAI-compatible local server (mlx_lm.server). The base URL is not secret but
    # is required, so it lives here rather than in a second configuration surface.
    "mlx": ProviderSpec(
        id="mlx",
        fields=(ProviderField(FIELD_BASE_URL, "MLX_BASE_URL", required=True),),
        model_prefixes=("openai-api/mlx/",),
        # This flag controls Connect-view inclusion; MLX still needs its URL configured.
        needs_credentials=True,
    ),
    "ollama": ProviderSpec(
        id="ollama", fields=(), model_prefixes=("ollama/",), needs_credentials=False,
    ),
}

# Longest prefix first so `openai-api/mlx/` wins over a hypothetical `openai-api/`.
_BY_PREFIX: tuple[tuple[str, ProviderSpec], ...] = tuple(
    sorted(
        ((prefix, spec) for spec in PROVIDERS.values() for prefix in spec.model_prefixes),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
)


def provider_for_model(model_id: str) -> ProviderSpec | None:
    """The provider a model string belongs to, or None for an unknown prefix."""
    for prefix, spec in _BY_PREFIX:
        if model_id.startswith(prefix):
            return spec
    return None


def configured_fields(spec: ProviderSpec, env: Mapping[str, str]) -> dict[str, bool]:
    """Per-field booleans. Whitespace-only is not configured."""
    return {field.id: bool(env.get(field.env_var, "").strip()) for field in spec.fields}


def is_configured(spec: ProviderSpec, env: Mapping[str, str]) -> bool:
    states = configured_fields(spec, env)
    return all(states[field.id] for field in spec.fields if field.required)
