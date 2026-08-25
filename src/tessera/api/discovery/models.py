"""Pure value types shared by discovery sources, merging, and caching."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ModelReadiness = Literal[
    "ready", "needs_key", "needs_server", "offline", "unverified"
]
ModelGroup = Literal["benchmark", "discovered"]
SourceStatus = Literal[
    "ready", "needs_key", "degraded", "unreachable", "offline"
]


@dataclass(frozen=True)
class DiscoveredModel:
    id: str
    label: str
    provider: str
    readiness: ModelReadiness
    group: ModelGroup = "discovered"
    detail: str | None = None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "provider": self.provider,
            "readiness": self.readiness,
            "group": self.group,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class SourceResult:
    source: str
    status: SourceStatus
    models: tuple[DiscoveredModel, ...] = field(default_factory=tuple)
    detail: str | None = None

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class DiscoverySnapshot:
    models: tuple[DiscoveredModel, ...]
    sources: tuple[SourceResult, ...]

    def as_dict(self) -> dict:
        return {
            "models": [model.as_dict() for model in self.models],
            "sources": [source.as_dict() for source in self.sources],
        }
