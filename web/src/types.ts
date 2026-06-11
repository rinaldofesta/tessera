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
export type TrendPoint = S["TrendPoint"];
export type StartRunResult = S["StartRunResult"];
export type RunStatus = S["RunStatus"];
export type RunConfig = S["RunRequest"];

// ----- blueprints (datasets) -----
export type Render = S["Render"];
export type Claim = S["Claim"];
export type ProbeDef = S["Probe"];
export type Blueprint = S["Blueprint"];
export type BlueprintMeta = S["BlueprintMeta"];
export type ValidationError = S["ValidationIssue"];
export type ValidationResult = S["ValidationResult"];
export type Artifacts = S["Artifacts"];
