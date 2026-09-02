"""Pure merge. No I/O, no clock, no network — every input arrives as an argument."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date

from tessera.api.providers import provider_for_model

from .types import DiscoveredModel, SourceResult, readiness_rank


def _published_placeholder(model_id: str) -> DiscoveredModel:
    """A published id no source confirmed. It is NOT ready: nothing observed it."""
    spec = provider_for_model(model_id)
    _, _, label = model_id.rpartition("/")
    return DiscoveredModel(
        id=model_id, label=label or model_id,
        provider=spec.id if spec else "unknown",
        readiness="needs_config", source="published",
    )


def merge(
    results: Iterable[SourceResult], published: Sequence[str],
) -> tuple[list[DiscoveredModel], list[SourceResult]]:
    """Dedupe by id, retain published provenance, and order providers by recency."""
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
    for model_id in published:
        ordered.append(best.get(model_id) or _published_placeholder(model_id))
        seen.add(model_id)
    for model_id, model in best.items():
        if model_id not in seen:
            ordered.append(model)

    # The picker renders published and additionally discovered sections separately.
    # Keep each section's first-seen provider order, but make each provider's rows
    # deterministic and useful: newest first, unknown or invalid dates last, then id.
    published_ids = set(published)
    provider_order: dict[tuple[bool, str], int] = {}
    for model in ordered:
        group = model.id not in published_ids
        provider_order.setdefault((group, model.provider), len(provider_order))

    def sort_key(model: DiscoveredModel) -> tuple[bool, int, bool, int, str]:
        group = model.id not in published_ids
        try:
            released = date.fromisoformat(model.released).toordinal() if model.released else None
        except ValueError:
            released = None
        return (
            group,
            provider_order[(group, model.provider)],
            released is None,
            -(released or 0),
            model.id,
        )

    return sorted(ordered, key=sort_key), statuses
