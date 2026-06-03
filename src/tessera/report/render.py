"""Pure Markdown rendering. No inspect_ai. (os.path is string-only, no filesystem access.)"""

from __future__ import annotations

import os

from tessera.report.models import (
    AxesSummary, CategoryReliability, ProbeReliability, RunHeader,
)

_CANONICAL_ORDER = ["none", "resolvable", "unresolvable", "void"]


def bar(rate: float, width: int = 10) -> str:
    n = round(rate * width)
    return "█" * n + "░" * (width - n)


def _pct(rate: float) -> str:
    return f"{rate * 100:.0f}%"
