import { act, cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Report } from "@/types";

vi.mock("@/api", () => ({ api: { watchRun: vi.fn(), getRun: vi.fn() } }));
import { api } from "@/api";
import { LiveRunPanel } from "./LiveRunPanel";

afterEach(cleanup);

class FakeSource {
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
}

const report: Report = {
  header: {
    model: "anthropic/claude-sonnet-4", engine: "deterministic", grader: null, org: "toy",
    k: 3, created: "2026-08-31T10:00:00Z", location: "l", scorer_version: null,
    inspect_ai_version: null, scaffold: "baseline", seed: 0, harness: "single",
  },
  overall: { pass_k_rate: 0.5, mean_rate: 0.75 },
  categories: [{ key: "unresolvable", n_probes: 2, pass_k_rate: 0.5, mean_rate: 0.75, flaky: true }],
  axes: { accuracy_rate: 1, provenance_rate: 1, refusal_rate: 0.5, n_answer_epochs: 3, n_refuse_epochs: 3, n_total_epochs: 6, answer_format_rate: null },
  probes: [
    { probe_id: "p1", conflict_type: "unresolvable", expected_behavior: "refuse", epochs_total: 3, epochs_passed: 1, pass_k: false, mean_pass: 0.33, failures: [] },
    { probe_id: "p2", conflict_type: "none", expected_behavior: "answer", epochs_total: 3, epochs_passed: 3, pass_k: true, mean_pass: 1, failures: [] },
  ],
};

const view = (source: FakeSource) => {
  vi.mocked(api.watchRun).mockReturnValue(source as unknown as EventSource);
  render(
    <MemoryRouter>
      <LiveRunPanel jobId="abc" questions={2} repeats={3} model="anthropic/claude-sonnet-4" suite="toy" />
    </MemoryRouter>,
  );
};

describe("LiveRunPanel", () => {
  it("shows the honest pending state while running: badge, mosaic, expected count", () => {
    view(new FakeSource());
    expect(screen.getByText("running…")).toBeInTheDocument();
    expect(screen.getByText("live — claude-sonnet-4 on toy")).toBeInTheDocument();
    expect(screen.getByText(/6 answers/)).toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it("fills atomically and shows the compact outcome with a detail link when done", async () => {
    const source = new FakeSource();
    vi.mocked(api.getRun).mockResolvedValue({
      status: "done", report, error: null,
      verdict: { pass_k_rate: 0.5, mean_rate: 0.75, label: "inconsistent", sentence: "Not reliable on disagreement." },
    });
    view(source);
    act(() => source.onmessage!({ data: JSON.stringify({ status: "done", error: null }) }));
    expect(await screen.findByText("Not reliable on disagreement.")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open run detail →" })).toHaveAttribute("href", "/reports/abc");
  });

  it("surfaces failure with the error text", async () => {
    const source = new FakeSource();
    vi.mocked(api.getRun).mockResolvedValue({ status: "error", report: null, verdict: null, error: "provider timeout" });
    view(source);
    act(() => source.onmessage!({ data: JSON.stringify({ status: "error", error: "provider timeout" }) }));
    expect(await screen.findByText("failed")).toBeInTheDocument();
    expect(screen.getByText("provider timeout")).toBeInTheDocument();
  });
});
