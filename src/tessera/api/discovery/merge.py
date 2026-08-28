"""Pure merge. No I/O, no clock, no network — every input arrives as an argument."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from tessera.api.providers import provider_for_model

from .types import DiscoveredModel, SourceResult, readiness_rank


def _curated_placeholder(model_id: str) -> DiscoveredModel:
    """A curated id no source confirmed. It is NOT ready: nothing observed it."""
    spec = provider_for_model(model_id)
    _, _, label = model_id.rpartition("/")
    return DiscoveredModel(
        id=model_id, label=label or model_id,
        provider=spec.id if spec else "unknown",
        readiness="needs_config", source="curated",
    )


def merge(
    results: Iterable[SourceResult], curated: Sequence[str],
) -> tuple[list[DiscoveredModel], list[SourceResult]]:
    """Dedupe by model id, keeping the best-evidenced readiness; curated ids first."""
    statuses = list(results)

    best: dict[str, DiscoveredModel] = {}
    for result in statuses:
        for model in result.models:
            incumbent = best.get(model.id)
            if incumbent is None or readiness_rank(model.readiness) > readiness_rank(
                incumbent.readiness
            ):
                best[model.id] = model

    ordered: list[DiscoveredModel] = []
    seen: set[str] = set()
    for model_id in curated:
        ordered.append(best.get(model_id) or _curated_placeholder(model_id))
        seen.add(model_id)
    for model_id, model in best.items():
        if model_id not in seen:
            ordered.append(model)
    return ordered, statuses
