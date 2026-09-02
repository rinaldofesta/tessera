"""ADR-0002 contract shared by every Tessera surface.

The CLI prints it, the API returns it, and the UI renders it. ``ok`` means the run
completed operationally; it never means that the agent is reliable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ReportHeader(BaseModel):
    model: str
    engine: str
    grader: str | None
    org: str | None
    k: int
    created: str
    location: str
    scorer_version: str | None = None  # det-4/llm-2 etc.; null on pre-versioned logs
    inspect_ai_version: str | None = None  # producing inspect_ai (from log packages); null if unrecorded
    scaffold: str | None = None  # prompt arm (ADR-0009); null on payloads serialized before it
    seed: int | None = None      # factory org instance (ADR-0008, 0 = authored); null on older payloads
    harness: str | None = None   # how model calls were dispatched (ADR-0011, "single"=lone model); null on older payloads


class ReportOverall(BaseModel):
    pass_k_rate: float
    mean_rate: float


class ReportCategory(BaseModel):
    key: str
    n_probes: int
    pass_k_rate: float
    mean_rate: float
    flaky: bool


class ReportAxes(BaseModel):
    accuracy_rate: float | None      # null when the org has no answer-probes
    provenance_rate: float           # never null (0.0 fallback)
    refusal_rate: float | None       # null when the org has no refuse-probes
    n_answer_epochs: int
    n_refuse_epochs: int
    n_total_epochs: int
    answer_format_rate: float | None = None  # null when the log never recorded the flag


class ReportFailure(BaseModel):
    epoch: int
    passed: bool
    accuracy_ok: bool
    provenance_ok: bool
    refusal_ok: bool
    question: str
    answer: str
    consulted: list[str]
    expected_sources: list[str]
    missing: list[str]
    answer_format_ok: bool | None = None  # det-2+ only; null on older logs


class ReportProbe(BaseModel):
    probe_id: str
    conflict_type: str
    expected_behavior: str
    epochs_total: int
    epochs_passed: int
    pass_k: bool
    mean_pass: float
    failures: list[ReportFailure]


class Report(BaseModel):
    header: ReportHeader
    overall: ReportOverall
    categories: list[ReportCategory]
    axes: ReportAxes
    probes: list[ReportProbe]


class ReceiptProtocol(BaseModel):
    org: str | None
    blueprint_sha256: str | None
    scaffold: str | None
    seed: int | None
    harness: str | None
    engine: str
    grader: str | None
    epochs: int
    scorer_version: str | None


class ReceiptRuntime(BaseModel):
    requested_model: str
    reported_model: str
    effective_models: list[str]
    inspect_ai_version: str | None
    tessera_version: str | None
    git_revision: str | None
    git_dirty: bool | None


class ReceiptArtifact(BaseModel):
    path: str
    sha256: str | None


class ReceiptTiming(BaseModel):
    started_at: str | None
    completed_at: str | None
    duration_seconds: float | None


class ReceiptUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    billed_cost: float | None


class RunReceipt(BaseModel):
    protocol_hash: str
    execution_hash: str
    protocol: ReceiptProtocol
    runtime: ReceiptRuntime
    artifact: ReceiptArtifact
    timing: ReceiptTiming
    usage: ReceiptUsage


class Diagnostic(BaseModel):
    """One aggregated failure signature from report.compare.diagnose_report."""

    kind: str
    signature: str
    count: int


RunStatus = Literal["queued", "running", "completed", "failed", "interrupted"]


class RunRequestSpec(BaseModel):
    suite: str
    model: str
    engine: Literal["deterministic", "llm"]
    grader: str | None
    k: int
    scaffold: str
    seed: int


class Verdict(BaseModel):
    pass_k_rate: float
    mean_rate: float
    label: Literal["reliable", "inconsistent", "unreliable"]


class Gate(BaseModel):
    min_pass_k: float
    passed: bool


class RunPaths(BaseModel):
    dir: str
    log: str | None
    report_json: str | None
    report_md: str | None


class Run(BaseModel):
    ok: bool
    id: str
    status: RunStatus
    source: Literal["run", "import", "bundled"]
    archived: bool
    schema_version: int
    created_at: str
    started_at: str | None
    finished_at: str | None
    request: RunRequestSpec
    verdict: Verdict | None
    gate: Gate | None
    report: Report | None
    receipt: RunReceipt | None
    diagnostics: list[Diagnostic]
    paths: RunPaths
    error: str | None
