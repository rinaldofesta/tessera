"""Response models for every JSON endpoint — the API's half of the single contract.

These models are the source the OpenAPI schema (and from it, the SPA's generated
TypeScript in web/src/api-types.gen.ts) is built from. FastAPI also validates every
response against them, so the whole key-free test suite doubles as a contract test:
if a handler's payload drifts from its model, a test fails before the SPA ever sees it.

Shape conventions: fields that are log-derived stay loose (str), fields the store
controls are closed Literals. Nullable-but-always-present keys are `X | None` with
no default, mirroring what the handlers actually emit.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from tessera.api.schemas import ExperimentRequest
from tessera.contract import Diagnostic, ReportAxes, RunReceipt
from tessera.contract import Report as Report  # re-export: routes still spell it R.Report

# ----- logs -----

class LogMeta(BaseModel):
    id: str                          # "source:stem"
    source: str
    path: str
    model: str
    engine: str
    grader: str | None
    org: str | None
    created: str
    k: int


class LeaderboardRow(BaseModel):
    label: str
    model: str
    date: str | None = None
    pass_k_rate: float
    mean_rate: float
    categories: dict[str, float]
    answer_format_rate: float | None = None
    scorer_version: str | None = None
    org: str | None = None
    k: int
    scaffold: str | None = None
    seed: int | None = None
    harness: str | None = None
    notes: str | None = None
    log: str | None = None


class LeaderboardManifest(BaseModel):
    title: str | None = None
    rows: list[LeaderboardRow]
    exhibitions: list[dict] = []


class TrendPoint(BaseModel):
    id: str
    created_at: str
    model: str
    org: str
    engine: str
    pass_k_rate: float
    mean_rate: float
    categories: dict[str, float]     # conflict-type key -> pass^k
    axes: ReportAxes


class EvaluationSummary(BaseModel):
    id: str
    kind: Literal["run", "log", "pinned", "import"]
    source: str
    status: Literal["done", "error"]
    created_at: str
    model: str
    org: str | None
    engine: str
    grader: str | None
    epochs: int
    pass_k_rate: float | None
    mean_rate: float | None
    artifact_path: str | None
    artifact_sha256: str | None
    protocol_hash: str
    execution_hash: str
    receipt: RunReceipt


class PairCounts(BaseModel):
    matched: int
    a_wins: int
    b_wins: int
    both_pass: int
    both_fail: int
    discordant: int
    p_value: float
    dropped: list[str]


class CategoryPairCounts(PairCounts):
    key: str


class ComparisonDiagnostics(BaseModel):
    a: list[Diagnostic]
    b: list[Diagnostic]


class ComparisonResult(BaseModel):
    compatible: bool
    intervention: str
    changed_dimensions: list[str]
    unexpected_dimensions: list[str]
    overall: PairCounts
    categories: list[CategoryPairCounts]
    diagnostics: ComparisonDiagnostics


# ----- paid capability preflight -----

class PreflightUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    billed_cost: float | None


class PreflightResult(BaseModel):
    model: str
    effective_model: str | None
    tool_call: bool
    ok: bool
    error: str | None
    latency_seconds: float
    checked_at: str
    cached: bool
    usage: PreflightUsage


# ----- experiments -----

ExperimentState = Literal["running", "done", "error", "stopped"]
CellState = Literal["pending", "running", "done", "error", "skipped"]


class ExperimentCell(BaseModel):
    id: str
    experiment_id: str
    variant_id: str
    repeat_index: int
    status: CellState
    run_id: str | None
    error: str | None


class Experiment(BaseModel):
    id: str
    name: str
    status: ExperimentState
    created_at: str
    updated_at: str
    baseline_variant: str
    request: ExperimentRequest
    error: str | None
    total_cost: float | None
    cells: list[ExperimentCell]


class ExperimentStarted(BaseModel):
    experiment_id: str
    status: ExperimentState


class ExperimentComparison(ComparisonResult):
    paired_repeats: list[int]
    dropped_repeats: list[int]


# ----- blueprints (datasets) -----

class BlueprintMeta(BaseModel):
    id: str
    claims: int
    probes: int


class ValidationIssue(BaseModel):
    location: str                    # dotted pydantic loc, or literal "compile"
    message: str


class ValidationResult(BaseModel):
    ok: bool
    errors: list[ValidationIssue]


class ManifestEntry(BaseModel):
    silo: str
    subject: str
    predicate: str
    artifact: str
    locator: str


class SiloField(BaseModel):
    value: Any
    asserted_at: str | None


class DocFile(BaseModel):
    path: str
    content: str


class Artifacts(BaseModel):
    manifest: dict[str, ManifestEntry]
    silos: dict[str, dict[str, dict[str, SiloField]]]
    docs: list[DocFile]


class BlueprintId(BaseModel):
    id: str


class BlueprintDeleted(BaseModel):
    deleted: str


# ----- eval setup (launcher vocabulary) -----

ModelReadiness = Literal["ready", "needs_config", "needs_server", "offline", "unverified"]
SuiteKind = Literal["builtin", "custom"]


class EvalSetupDefaults(BaseModel):
    engine: Literal["deterministic"]
    repeats: int
    grader: str | None


class EvalSetupModel(BaseModel):
    id: str
    label: str
    provider: str
    readiness: ModelReadiness
    source: str
    published: bool
    released: str | None
    retired: bool
    detail: str | None = None


class EvalSetupSuite(BaseModel):
    id: str
    kind: SuiteKind
    editable: bool
    claims: int
    questions: int


class EvalSetup(BaseModel):
    defaults: EvalSetupDefaults
    models: list[EvalSetupModel]
    suites: list[EvalSetupSuite]
    sources: list[SourceStatus]


# ----- providers (credential configuration) -----

ProviderReadiness = Literal["configured", "needs_config"]


class ProviderField(BaseModel):
    id: str
    env_var: str
    configured: bool


class Provider(BaseModel):
    id: str
    configured: bool
    readiness: ProviderReadiness
    fields: list[ProviderField]


class SourceStatus(BaseModel):
    source: str
    status: Literal["ok", "offline", "skipped"]
    detail: str | None


class RescanResult(BaseModel):
    sources: list[SourceStatus]
    model_count: int
