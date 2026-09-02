"""The vocabulary every source speaks. No logic lives here."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Five states, because the old two-value guess could not express "installed but not
# served" or "the daemon is down". `needs_config` covers any unmet requirement; the
# per-field booleans on the provider say which one.
Readiness = Literal["ready", "needs_config", "needs_server", "offline", "unverified"]

SourceStatusValue = Literal["ok", "offline", "skipped"]

# Ranked worst-to-best so a duplicate collapses to the best evidence any source has.
_RANK: dict[str, int] = {
    "offline": 0, "needs_config": 1, "needs_server": 2, "unverified": 3, "ready": 4,
}


def readiness_rank(readiness: str) -> int:
    return _RANK.get(readiness, 0)


@dataclass(frozen=True)
class DiscoveredModel:
    id: str
    label: str
    provider: str
    readiness: Readiness
    source: str
    detail: str | None = None      # e.g. the command that would serve an MLX model
    released: str | None = None    # ISO date when the provider reports one
    retired: bool = False          # provider has announced a shutdown date


@dataclass(frozen=True)
class SourceResult:
    source: str
    models: tuple[DiscoveredModel, ...]
    status: SourceStatusValue
    detail: str | None = None
