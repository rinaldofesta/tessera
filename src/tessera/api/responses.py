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

RunState = Literal["running", "done", "error"]


# ----- report (the scorecard JSON from report.serialize.report_to_dict) -----

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


# ----- runs -----

class StartRunResult(BaseModel):
    job_id: str
    status: RunState


class RunStatus(BaseModel):
    status: RunState
    report: Report | None            # set once the run is done
    error: str | None                # set when status == "error"


class RunSummary(BaseModel):
    id: str
    status: RunState
    error: str | None
    model: str
    org: str
    judge: str
    grader: str | None
    epochs: int
    created_at: str
    finished_at: str | None
    pass_k_rate: float | None        # null until a report exists
    mean_rate: float | None


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

ModelReadiness = Literal["ready", "missing_credentials", "unknown"]
SuiteKind = Literal["builtin", "custom"]


class EvalSetupDefaults(BaseModel):
    engine: Literal["deterministic"]
    repeats: int
    model: str
    grader: str | None


class EvalSetupModel(BaseModel):
    id: str
    label: str
    provider: str
    readiness: ModelReadiness


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
