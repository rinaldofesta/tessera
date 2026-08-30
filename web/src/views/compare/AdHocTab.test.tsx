import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ComparisonResult, EvaluationSummary, Report } from "@/types";

vi.mock("@/api", () => ({
  api: {
    listEvaluations: vi.fn(),
    getEvaluationReport: vi.fn(),
    evaluationDiagnostics: vi.fn().mockResolvedValue([]),
    compareEvaluations: vi.fn(),
    uploadReport: vi.fn(),
    importEvaluation: vi.fn(),
  },
}));
import { api } from "@/api";
import AdHocTab from "./AdHocTab";

afterEach(cleanup);

const ev = (id: string, model: string): EvaluationSummary =>
  ({
    id, kind: "run", source: "api", status: "done",
    created_at: "2026-08-29T14:02:11Z", model, org: "meridian", engine: "llm",
    grader: null, epochs: 3, pass_k_rate: 0.72, mean_rate: 0.94,
    artifact_path: null, artifact_sha256: null, protocol_hash: "p", execution_hash: "x",
    receipt: {
      protocol_hash: "p", execution_hash: "x", protocol: {}, artifact: {},
      runtime: { effective_models: [] }, timing: { duration_seconds: null }, usage: { billed_cost: null },
    },
  }) as unknown as EvaluationSummary;

const report: Report = {
  header: {
    model: "m", engine: "llm", grader: null, org: "meridian", k: 3,
    created: "2026-08-29T14:02:11Z", location: "l", scorer_version: null,
    inspect_ai_version: null, scaffold: "baseline", seed: 0, harness: "single",
  },
  overall: { pass_k_rate: 0.72, mean_rate: 0.94 },
  categories: [{ key: "unresolvable", n_probes: 2, pass_k_rate: 0.5, mean_rate: 0.75, flaky: true }],
  axes: {
    accuracy_rate: 0.8, provenance_rate: 0.9, refusal_rate: 0.5,
    n_answer_epochs: 4, n_refuse_epochs: 2, n_total_epochs: 6, answer_format_rate: null,
  },
  probes: [],
};

const comparison = (compatible: boolean, unexpected: string[] = []): ComparisonResult => ({
  compatible, intervention: "model",
  changed_dimensions: ["model"], unexpected_dimensions: unexpected,
  overall: {
    matched: 12, a_wins: 2, b_wins: 5,
    both_pass: 4, both_fail: 1, discordant: 7, p_value: 0.0312, dropped: [],
  },
  categories: [],
  diagnostics: { a: [], b: [] },
});

const view = (search = "") =>
  render(
    <MemoryRouter initialEntries={[`/compare${search}`]}>
      <AdHocTab />
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.mocked(api.listEvaluations).mockReset();
  vi.mocked(api.compareEvaluations).mockReset();
  vi.mocked(api.getEvaluationReport).mockResolvedValue(report);
});

describe("AdHocTab", () => {
  it("asks for two selections before comparing", async () => {
    vi.mocked(api.listEvaluations).mockResolvedValue([ev("run:a", "x/a")]);
    view();
    expect(await screen.findByText("select at least two evaluations to compare")).toBeInTheDocument();
    expect(api.compareEvaluations).not.toHaveBeenCalled();
  });

  it("seeds selection from ?evals= and fires N−1 pairwise calls, baseline first", async () => {
    vi.mocked(api.listEvaluations).mockResolvedValue([
      ev("run:a", "x/a"), ev("run:b", "x/b"), ev("run:c", "x/c"),
    ]);
    vi.mocked(api.compareEvaluations).mockResolvedValue(comparison(true));
    view("?evals=run:b,run:a,run:c");
    await waitFor(() => expect(api.compareEvaluations).toHaveBeenCalledTimes(2));
    expect(api.compareEvaluations).toHaveBeenCalledWith("run:b", "run:a", "model");
    expect(api.compareEvaluations).toHaveBeenCalledWith("run:b", "run:c", "model");
    expect(await screen.findByText("Controlled comparison")).toBeInTheDocument();
  });

  it("drops unknown ids from the ?evals= seed", async () => {
    vi.mocked(api.listEvaluations).mockResolvedValue([ev("run:a", "x/a")]);
    view("?evals=run:a,run:ghost");
    expect(await screen.findByText("select at least two evaluations to compare")).toBeInTheDocument();
  });

  it("raises the drift banner with per-challenger dimensions", async () => {
    vi.mocked(api.listEvaluations).mockResolvedValue([ev("run:a", "x/a"), ev("run:b", "x/b")]);
    vi.mocked(api.compareEvaluations).mockResolvedValue(comparison(false, ["seed", "k"]));
    view("?evals=run:a,run:b");
    expect(await screen.findByText("Protocol drift detected")).toBeInTheDocument();
    expect(screen.getByText(/run:b: unexpected seed, k/)).toBeInTheDocument();
  });

  it("shows the significance table only for exactly two selections", async () => {
    vi.mocked(api.listEvaluations).mockResolvedValue([
      ev("run:a", "x/a"), ev("run:b", "x/b"), ev("run:c", "x/c"),
    ]);
    vi.mocked(api.compareEvaluations).mockResolvedValue(comparison(true));
    const { unmount } = view("?evals=run:a,run:b");
    expect(await screen.findByText("paired outcomes — probe × repeat")).toBeInTheDocument();
    unmount();
    view("?evals=run:a,run:b,run:c");
    await waitFor(() => expect(api.compareEvaluations).toHaveBeenCalled());
    expect(screen.queryByText("paired outcomes — probe × repeat")).not.toBeInTheDocument();
  });

  it("renders one gap bar per selection", async () => {
    vi.mocked(api.listEvaluations).mockResolvedValue([ev("run:a", "x/a"), ev("run:b", "x/b")]);
    vi.mocked(api.compareEvaluations).mockResolvedValue(comparison(true));
    view("?evals=run:a,run:b");
    await screen.findByText("Controlled comparison");
    const bars = screen.getAllByRole("img").filter((el) =>
      el.getAttribute("aria-label")?.includes("reliable (pass^"),
    );
    expect(bars).toHaveLength(2);
  });
});
