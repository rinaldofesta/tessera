import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { EvalSetup, EvaluationSummary, Report } from "@/types";

vi.mock("@/api", () => ({
  api: {
    listEvaluations: vi.fn(),
    getEvaluationReport: vi.fn(),
    evaluationDiagnostics: vi.fn().mockResolvedValue([]),
    compareEvaluations: vi.fn(),
    uploadReport: vi.fn(),
    importEvaluation: vi.fn(),
    evalSetup: vi.fn(),
    listExperiments: vi.fn(),
    preflight: vi.fn(),
    startExperiment: vi.fn(),
    resumeExperiment: vi.fn(),
    compareExperiment: vi.fn(),
  },
}));
import { api } from "@/api";
import Compare from "./Compare";

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

const setup: EvalSetup = {
  defaults: { engine: "deterministic", grader: null, repeats: 3 },
  models: [], suites: [], sources: [],
};

const report: Report = {
  header: {
    model: "m", engine: "llm", grader: null, org: "meridian", k: 3,
    created: "2026-08-29T14:02:11Z", location: "l", scorer_version: null,
    inspect_ai_version: null, scaffold: "baseline", seed: 0, harness: "single",
  },
  overall: { pass_k_rate: 0.72, mean_rate: 0.94 },
  categories: [],
  axes: {
    accuracy_rate: 0.8, provenance_rate: 0.9, refusal_rate: 0.5,
    n_answer_epochs: 4, n_refuse_epochs: 2, n_total_epochs: 6, answer_format_rate: null,
  },
  probes: [],
};

describe("Compare", () => {
  it("keeps a tab's state when switching away and back (no unmount-and-reseed)", async () => {
    vi.mocked(api.listEvaluations).mockResolvedValue([ev("run:a", "x/a"), ev("run:b", "x/b")]);
    vi.mocked(api.getEvaluationReport).mockResolvedValue(report);
    vi.mocked(api.compareEvaluations).mockResolvedValue({} as never);
    vi.mocked(api.evalSetup).mockResolvedValue(setup);
    vi.mocked(api.listExperiments).mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/compare"]}>
        <Compare />
      </MemoryRouter>,
    );

    const checkbox = await screen.findByRole("checkbox", { name: /^a ·/ });
    await userEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    await userEvent.click(screen.getByRole("tab", { name: "experiments" }));
    await waitFor(() => expect(screen.getByRole("tab", { name: "experiments" })).toHaveAttribute("aria-selected", "true"));
    await screen.findByText("new controlled experiment");

    await userEvent.click(screen.getByRole("tab", { name: "ad-hoc" }));
    await waitFor(() => expect(screen.getByRole("checkbox", { name: /^a ·/ })).toBeChecked());
  });
});
