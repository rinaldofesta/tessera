// The API contract, aliased from the GENERATED types in api-types.gen.ts — which
// openapi-typescript builds from openapi.json, which FastAPI builds from the Pydantic
// response models in src/tessera/api/responses.py. One source of truth, end to end:
// regenerate with `bash scripts/gen-types.sh`; CI fails if these files drift.
//
// This file only maps generated schema names onto the names the views import —
// never declare a shape by hand here.

import type { components } from "./api-types.gen";

type S = components["schemas"];

// ----- reports (scorecards) -----
export type ReportHeader = S["ReportHeader"];
export type Category = S["ReportCategory"];
export type Axes = S["ReportAxes"];
export type FailureEpoch = S["ReportFailure"];
export type Probe = S["ReportProbe"];
export type Report = S["Report"];

// ----- logs + runs -----
export type LogMeta = S["LogMeta"];
export type RunSummary = S["RunSummary"];
export type LeaderboardManifest = S["LeaderboardManifest"];
export type LeaderboardRow = S["LeaderboardRow"];
export type TrendPoint = S["TrendPoint"];
export type StartRunResult = S["StartRunResult"];
export type RunStatus = S["RunStatus"];
export type RunConfig = S["RunRequest"];
export type RunReceipt = S["RunReceipt"];
export type EvaluationSummary = S["EvaluationSummary"];
export type ComparisonResult = S["ComparisonResult"];
export type Diagnostic = S["Diagnostic"];
export type ComparisonIntervention = NonNullable<S["ComparisonRequest"]["intervention"]>;
export type PreflightResult = S["PreflightResult"];
export type Experiment = S["Experiment"];
export type ExperimentRequest = S["ExperimentRequest"];
export type ExperimentStarted = S["ExperimentStarted"];
export type ExperimentComparison = S["ExperimentComparison"];

// ----- blueprints (datasets) -----
export type Render = S["Render"];
export type Claim = S["Claim"];
export type ProbeDef = S["Probe"];
export type Blueprint = S["Blueprint"];
export type BlueprintMeta = S["BlueprintMeta"];
export type ValidationError = S["ValidationIssue"];
export type ValidationResult = S["ValidationResult"];
export type Artifacts = S["Artifacts"];

// ----- eval setup + providers (the guided launcher) -----
export type EvalSetup = S["EvalSetup"];
export type EvalSetupModel = S["EvalSetupModel"];
export type EvalSetupSuite = S["EvalSetupSuite"];
export type Provider = S["Provider"];
export type ProviderField = S["ProviderField"];
export type ProviderUpdate = S["ProviderUpdate"];
export type SourceStatus = S["SourceStatus"];
export type RescanResult = S["RescanResult"];
