// The API contract, aliased from the GENERATED types in api-types.gen.ts — which
// openapi-typescript builds from openapi.json, which FastAPI builds from the Pydantic
// response models in src/tessera/api/responses.py. One source of truth, end to end:
// regenerate with `bash scripts/gen-types.sh`; CI fails if these files drift.
//
import type { components } from "./api-types.gen";

type S = components["schemas"];

// ----- reports (scorecards) -----
export type ReportHeader = S["ReportHeader"];
export type Category = S["ReportCategory"];
export type Axes = S["ReportAxes"];
export type FailureEpoch = S["ReportFailure"];
export type Probe = S["ReportProbe"];
export type Report = S["Report"];

// ----- runs -----
export type Run = S["Run"];
export type RunSpec = S["RunSpec"];
export type Blocker = S["Blocker"];
export type Plan = S["Plan"];
export type ComparisonResult = S["ComparisonResult"];
export type ComparisonIntervention = NonNullable<S["ComparisonRequest"]["intervention"]>;

// ----- blueprints (datasets) -----
export type Render = S["Render"];
export type Claim = S["Claim"];
export type ProbeDef = S["Probe"];
export type Blueprint = S["Blueprint"];
export type BlueprintMeta = S["BlueprintMeta"];
export type ValidationError = S["ValidationIssue"];
export type ValidationResult = S["ValidationResult"];
export type Artifacts = S["Artifacts"];

// ----- catalog + provider configuration -----
export type Catalog = S["Catalog"];
export type CatalogModel = S["CatalogModel"];
export type CatalogProvider = S["CatalogProvider"];
export type CatalogSuite = S["CatalogSuite"];
export type Provider = S["Provider"];
export type ProviderField = S["ProviderField"];
export type ProviderUpdate = S["ProviderUpdate"];
