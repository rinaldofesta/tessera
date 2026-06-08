// Types mirroring the FastAPI JSON contract (src/tessera/...). Kept in one place so the
// SPA has a single source of truth; a future step generates these from the OpenAPI schema.

export interface ReportHeader {
  model: string;
  engine: string;
  grader: string | null;
  org: string | null;
  k: number;
  created: string;
  location: string;
}
export interface Category {
  key: string;
  n_probes: number;
  pass_k_rate: number;
  mean_rate: number;
  flaky: boolean;
}
export interface Axes {
  accuracy_rate: number | null;
  provenance_rate: number;
  refusal_rate: number | null;
  n_answer_epochs: number;
  n_refuse_epochs: number;
  n_total_epochs: number;
}
export interface FailureEpoch {
  epoch: number;
  passed: boolean;
  accuracy_ok: boolean;
  provenance_ok: boolean;
  refusal_ok: boolean;
  question: string;
  answer: string;
  consulted: string[];
  expected_sources: string[];
  missing: string[];
}
export interface Probe {
  probe_id: string;
  conflict_type: string;
  expected_behavior: string;
  epochs_total: number;
  epochs_passed: number;
  pass_k: boolean;
  mean_pass: number;
  failures: FailureEpoch[];
}
export interface Report {
  header: ReportHeader;
  overall: { pass_k_rate: number; mean_rate: number };
  categories: Category[];
  axes: Axes;
  probes: Probe[];
}

export interface LogMeta {
  id: string;
  source: string;
  model: string;
  engine: string;
  grader: string | null;
  org: string | null;
  created: string;
  k: number;
}
export interface RunSummary {
  id: string;
  status: "running" | "done" | "error";
  model: string;
  org: string;
  judge: string;
  grader: string | null;
  epochs: number;
  created_at: string;
  finished_at: string | null;
  error: string | null;
  pass_k_rate: number | null;
  mean_rate: number | null;
}
export interface TrendPoint {
  id: string;
  created_at: string;
  model: string;
  org: string;
  engine: string;
  pass_k_rate: number;
  mean_rate: number;
  categories: Record<string, number>;
  axes: Axes;
}

// ----- blueprints (datasets) -----
export interface Render {
  as: "field" | "prose";
  template?: string | null;
}
export interface Claim {
  claim_id: string;
  subject: string;
  predicate: string;
  value: unknown;
  silo: string;
  asserted_at?: string | null;
  authority?: number | null;
  render: Render;
}
export interface ProbeDef {
  probe_id: string;
  question: string;
  references: string[];
  conflict_type: "none" | "resolvable" | "unresolvable" | "void";
  resolution_rule?: "recency_wins" | "authority_wins" | null;
  expected_behavior: "answer" | "refuse";
  expected_answer?: string | null;
  expected_sources: string[];
}
export interface Blueprint {
  claims: Claim[];
  probes: ProbeDef[];
}
export interface BlueprintMeta {
  id: string;
  claims: number;
  probes: number;
}
export interface ValidationError {
  location: string;
  message: string;
}
export interface ValidationResult {
  ok: boolean;
  errors: ValidationError[];
}
export interface Artifacts {
  manifest: Record<string, unknown>;
  silos: Record<string, Record<string, Record<string, { value: unknown; asserted_at: string | null }>>>;
  docs: { path: string; content: string }[];
}
export interface RunConfig {
  model: string;
  judge: string;
  org: string;
  grader?: string;
  epochs: number;
}
