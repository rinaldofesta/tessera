import type { ComparisonResult, Report, Run } from "@/types";

export const reportFixture: Report = {
  header: {
    model: "anthropic/claude-sonnet-4", engine: "deterministic", grader: null, org: "starter",
    k: 3, created: "2026-09-02T10:00:00Z", location: "logs/run.eval", scorer_version: "det-4",
    inspect_ai_version: "0.3", scaffold: "baseline", seed: 0, harness: "single",
  },
  overall: { pass_k_rate: 0.5, mean_rate: 0.75 },
  categories: [
    { key: "unresolvable", n_probes: 1, pass_k_rate: 0, mean_rate: 0.5, flaky: true },
    { key: "none", n_probes: 1, pass_k_rate: 1, mean_rate: 1, flaky: false },
  ],
  axes: { accuracy_rate: 0.75, provenance_rate: 1, refusal_rate: 0.5, n_answer_epochs: 3, n_refuse_epochs: 3, n_total_epochs: 6, answer_format_rate: null },
  probes: [
    {
      probe_id: "p1", conflict_type: "unresolvable", expected_behavior: "refuse",
      epochs_total: 3, epochs_passed: 1, pass_k: false, mean_pass: 1 / 3,
      failures: [{ epoch: 2, passed: false, accuracy_ok: false, provenance_ok: true, refusal_ok: false, question: "Which value is correct?", answer: "The first value.", consulted: ["crm"], expected_sources: ["crm", "wiki"], missing: ["wiki"], answer_format_ok: null }],
    },
    { probe_id: "p2", conflict_type: "none", expected_behavior: "answer", epochs_total: 3, epochs_passed: 3, pass_k: true, mean_pass: 1, failures: [] },
  ],
};

export function runFixture(overrides: Partial<Run> = {}): Run {
  return {
    ok: true, id: "run-1", status: "completed", source: "run", archived: false, schema_version: 1,
    created_at: "2026-09-02T10:00:00Z", started_at: "2026-09-02T10:00:01Z", finished_at: "2026-09-02T10:01:00Z",
    request: { suite: "starter", model: "anthropic/claude-sonnet-4", engine: "deterministic", grader: null, k: 3, scaffold: "baseline", seed: 0 },
    verdict: { pass_k_rate: 0.5, mean_rate: 0.75, label: "inconsistent", sentence: "Not reliable. Right every time on 1 of 2 questions." },
    gate: null, report: reportFixture,
    receipt: {
      artifact: { path: "logs/run.eval", sha256: "abc" }, execution_hash: "execution", protocol_hash: "protocol",
      protocol: { blueprint_sha256: "blueprint", engine: "deterministic", epochs: 3, grader: null, harness: "single", org: "starter", scaffold: "baseline", scorer_version: "det-4", seed: 0 },
      runtime: { effective_models: ["anthropic/claude-sonnet-4"], git_dirty: false, git_revision: "abc123", inspect_ai_version: "0.3", reported_model: "anthropic/claude-sonnet-4", requested_model: "anthropic/claude-sonnet-4", tessera_version: "0.3" },
      timing: { completed_at: "2026-09-02T10:01:00Z", duration_seconds: 59, started_at: "2026-09-02T10:00:01Z" },
      usage: { billed_cost: null, input_tokens: 10, output_tokens: 20, total_tokens: 30 },
    },
    diagnostics: [{ kind: "refusal", signature: "missed refusal", count: 1 }],
    paths: { dir: "/runs/run-1", log: "logs/run.eval", report_json: "report.json", report_md: "report.md" }, error: null,
    ...overrides,
  };
}

export const comparisonFixture: ComparisonResult = {
  compatible: false, intervention: "model", changed_dimensions: ["model"], unexpected_dimensions: ["grader"],
  diagnostics: { a: [], b: [] },
  overall: { a_wins: 1, b_wins: 2, both_pass: 3, both_fail: 4, discordant: 3, dropped: [], matched: 10, p_value: 0.25 },
  categories: [{ key: "unresolvable", a_wins: 1, b_wins: 2, both_pass: 0, both_fail: 1, discordant: 3, dropped: [], matched: 4, p_value: 0.5 }],
};
