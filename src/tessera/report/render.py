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


def render_scorecard(header: RunHeader, overall_pass_k: float, overall_mean: float,
                     categories: list[CategoryReliability]) -> str:
    by_key = {c.key: c for c in categories}
    lines = [
        f"## Reliability — pass^{header.k} (strict)",
        "```text",
        f"OVERALL  pass^{header.k}  {_pct(overall_pass_k)}   (mean {_pct(overall_mean)})",
        "",
        f"by conflict type        pass^{header.k}            mean",
    ]
    for key in _CANONICAL_ORDER:
        c = by_key.get(key)
        if c is None:
            continue
        flaky = "  ⚠ flaky" if c.mean_rate > c.pass_k_rate else ""
        lines.append(
            f"  {key:<13} {bar(c.pass_k_rate)} {_pct(c.pass_k_rate):>4}"
            f"           {_pct(c.mean_rate):>4}{flaky}"
        )
    lines.append("```")
    return "\n".join(lines)
