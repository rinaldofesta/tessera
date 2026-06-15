"""Pure data structures for the Tessera report. No inspect_ai, no I/O."""

from __future__ import annotations

from dataclasses import dataclass

# Canonical conflict-type order, mirroring the taxonomy in `tessera.models.ConflictType`.
# Single source of truth: every renderer (scorecard, JSON serializer, leaderboard) orders
# its category columns by this list, so the Markdown report and the API JSON never diverge.
CANONICAL_ORDER = ["none", "resolvable", "unresolvable", "void"]


class ReportError(Exception):
    """Expected, user-facing failure (bad/empty/foreign log). The CLI prints it and exits 2."""


@dataclass(frozen=True)
class ProbeEpoch:
    """One (probe x epoch) outcome, normalized off an EvalSample."""

    probe_id: str
    epoch: int
    conflict_type: str
    expected_behavior: str            # "answer" | "refuse"
    passed: bool
    accuracy_ok: bool
    provenance_ok: bool
    refusal_ok: bool
    consulted: tuple[str, ...]
    expected_sources: tuple[str, ...]
    question: str
    answer: str
    expected_answer: str | None
    answer_format_ok: bool | None = None  # det-2+ only; None when the log predates it


@dataclass(frozen=True)
class RunHeader:
    model: str
    engine: str                       # "deterministic" | "llm"
    k: int
    created: str
    location: str
    grader: str | None
    org: str | None = None            # which blueprint was evaluated (if recorded)
    scorer_version: str | None = None # det-4/llm-2 etc.; None on pre-versioned logs


@dataclass(frozen=True)
class ProbeReliability:
    probe_id: str
    conflict_type: str
    expected_behavior: str
    epochs_total: int
    epochs_passed: int
    pass_k: bool                      # epochs_passed == epochs_total (strict)
    mean_pass: float
    failures: tuple[ProbeEpoch, ...]


@dataclass(frozen=True)
class CategoryReliability:
    key: str
    n_probes: int
    pass_k_rate: float
    mean_rate: float


@dataclass(frozen=True)
class AxesSummary:
    accuracy_rate: float | None
    provenance_rate: float
    refusal_rate: float | None
    n_answer_epochs: int
    n_refuse_epochs: int
    n_total_epochs: int
    answer_format_rate: float | None = None  # over format-flagged epochs; None if unflagged
