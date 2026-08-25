"""Pure benchmark construction and discovered-model merging."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from tessera.api.discovery.cloud import CREDENTIAL_ENV
from tessera.api.discovery.models import (
    DiscoveredModel,
    DiscoverySnapshot,
    ModelReadiness,
    SourceResult,
)

DEFAULT_BENCHMARK_IDS = (
    "anthropic/claude-sonnet-4-6",
    "openai/gpt-4o",
    "anthropic/claude-opus-4-8",
    "anthropic/claude-haiku-4-5",
    "openai/gpt-4o-mini",
    "ollama/qwen3.5:latest",
)


def _configured_model_ids(environ: Mapping[str, str]) -> list[str]:
    return [
        model.strip()
        for model in environ.get("TESSERA_MODELS", "").split(",")
        if model.strip()
    ]


def resolved_model_ids(environ: Mapping[str, str]) -> list[str]:
    configured = _configured_model_ids(environ)
    return configured or list(DEFAULT_BENCHMARK_IDS)


def _model_parts(model_id: str) -> tuple[str, str]:
    if model_id.startswith("openai-api/mlx/"):
        return "mlx", model_id.removeprefix("openai-api/mlx/")
    provider, separator, label = model_id.partition("/")
    return (provider, label) if separator else ("unknown", model_id)


def benchmark_models(environ: Mapping[str, str]) -> tuple[DiscoveredModel, ...]:
    custom = bool(_configured_model_ids(environ))
    models: list[DiscoveredModel] = []
    for model_id in resolved_model_ids(environ):
        provider, label = _model_parts(model_id)
        readiness: ModelReadiness = "unverified"
        detail = "Custom model; availability has not been verified" if custom else None
        if not custom and provider in CREDENTIAL_ENV:
            env_name = CREDENTIAL_ENV[provider]
            if not environ.get(env_name, "").strip():
                readiness = "needs_key"
                detail = f"Set {env_name}"
            else:
                detail = "Waiting for provider verification"
        elif not custom and provider in {"ollama", "mlx", "openai-api"}:
            readiness = "offline"
            detail = "Local runtime has not been verified"
        models.append(DiscoveredModel(
            id=model_id,
            label=label,
            provider=provider,
            readiness=readiness,
            group="benchmark",
            detail=detail,
        ))
    return tuple(models)


def merge_models(
    curated: Sequence[DiscoveredModel],
    source_results: Sequence[SourceResult],
) -> DiscoverySnapshot:
    """Dedupe by id while preserving curated identity/order and source truth."""
    ordered_ids = list(dict.fromkeys(model.id for model in curated))
    models = {model.id: model for model in curated}
    discovered: dict[str, DiscoveredModel] = {}

    for source in source_results:
        for model in source.models:
            current = models.get(model.id)
            if current is not None:
                # The benchmark row remains visibly curated, while its live readiness
                # comes from the source that actually checked it.
                models[model.id] = DiscoveredModel(
                    id=current.id,
                    label=current.label,
                    provider=current.provider,
                    readiness=model.readiness,
                    group="benchmark",
                    detail=model.detail,
                )
            else:
                discovered[model.id] = model

    for model_id in sorted(
        discovered,
        key=lambda item: (
            discovered[item].provider.lower(),
            discovered[item].label.lower(),
            item,
        ),
    ):
        ordered_ids.append(model_id)
        models[model_id] = discovered[model_id]

    return DiscoverySnapshot(
        models=tuple(models[model_id] for model_id in ordered_ids),
        sources=tuple(source_results),
    )
