import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Report } from "@/types";

vi.mock("@/api", () => ({
  api: {
    watchRun: vi.fn(),
    getRun: vi.fn(),
    listRuns: vi.fn().mockResolvedValue([]),
    evalSetup: vi.fn().mockResolvedValue({
      suites: [], models: [], sources: [], defaults: { engine: "deterministic", repeats: 3 },
    }),
  },
}));
vi.mock("@/lib/download", () => ({ downloadText: vi.fn() }));
import { api } from "@/api";
import { downloadText } from "@/lib/download";
import RunMonitor from "./RunMonitor";

afterEach(cleanup);

const report: Report = {
  header: {
    model: "anthropic/claude-sonnet-4", engine: "deterministic", grader: null, org: "toy",
    k: 3, created: "2026-08-29T14:02:11Z", location: "l", scorer_version: "det-4",
    inspect_ai_version: null, scaffold: "baseline", seed: 0, harness: "single",
  },
  overall: { pass_k_rate: 1, mean_rate: 1 },
  categories: [{ key: "none", n_probes: 1, pass_k_rate: 1, mean_rate: 1, flaky: false }],
  axes: {
    accuracy_rate: 1, provenance_rate: 1, refusal_rate: null, n_answer_epochs: 3,
    n_refuse_epochs: 0, n_total_epochs: 3, answer_format_rate: null,
  },
  probes: [{
    probe_id: "p1", conflict_type: "none", expected_behavior: "answer", epochs_total: 3,
    epochs_passed: 3, pass_k: true, mean_pass: 1, failures: [],
  }],
};

class FakeSource {
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
}

const view = () =>
  render(
    <MemoryRouter initialEntries={["/runs/abc"]}>
      <Routes><Route path="/runs/:id" element={<RunMonitor />} /></Routes>
    </MemoryRouter>,
  );

describe("RunMonitor as run detail", () => {
  it("shows the scorecard and export buttons once the run is done", async () => {
    const source = new FakeSource();
    vi.mocked(api.watchRun).mockReturnValue(source as unknown as EventSource);
    vi.mocked(api.getRun).mockResolvedValue({ status: "done", report, error: null });
    view();
    source.onmessage!({ data: JSON.stringify({ status: "done", error: null }) });
    expect(await screen.findByText(/Reliable — correct behavior/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Export HTML" }));
    expect(vi.mocked(downloadText)).toHaveBeenCalledWith(
      "tessera-toy-claude-sonnet-4-2026-08-29.html",
      expect.stringContaining("<!doctype html>"),
      "text/html",
    );
  });
});
