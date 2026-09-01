import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RunSummary } from "@/types";

vi.mock("@/api", () => ({ api: { listRuns: vi.fn(), getRun: vi.fn() } }));
vi.mock("@/lib/download", () => ({ downloadText: vi.fn() }));
import { api } from "@/api";
import { downloadText } from "@/lib/download";
import RunHistory from "./RunHistory";

const run = (over: Partial<RunSummary>): RunSummary => ({
  id: "id0",
  status: "done",
  error: null,
  model: "anthropic/claude-sonnet-4",
  org: "meridian",
  judge: "llm",
  grader: null,
  epochs: 5,
  created_at: "2026-08-29T14:02:11Z",
  finished_at: "2026-08-29T14:31:40Z",
  pass_k_rate: 0.72,
  mean_rate: 0.94,
  archived: false,
  ...over,
});

const view = () =>
  render(
    <MemoryRouter>
      <RunHistory />
    </MemoryRouter>,
  );

afterEach(cleanup);

// No beforeEach mock reset: with vitest 4.1, clearing/resetting this mock in a
// hook makes the error test's rejection count as unhandled. Every test installs
// its own implementation, so nothing leaks between tests.
describe("RunHistory", () => {
  it("lists runs from the raw store", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      run({ id: "a", model: "anthropic/claude-sonnet-4" }),
      run({ id: "b", model: "openai/gpt-5.2", org: "toy" }),
    ]);
    view();
    expect(await screen.findByText("claude-sonnet-4")).toBeInTheDocument();
    expect(screen.getByText("gpt-5.2")).toBeInTheDocument();
    expect(screen.getByText("2 runs")).toBeInTheDocument();
  });

  it("filters by substring across model, suite, and grader", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      run({ id: "a", model: "anthropic/claude-sonnet-4" }),
      run({ id: "b", model: "openai/gpt-5.2", org: "toy" }),
    ]);
    view();
    await screen.findAllByText("claude-sonnet-4");
    await userEvent.type(screen.getByPlaceholderText("filter by model, suite, or grader…"), "toy");
    expect(screen.queryByText("claude-sonnet-4")).not.toBeInTheDocument();
    expect(screen.getByText("gpt-5.2")).toBeInTheDocument();
    expect(screen.getByText("1 of 2 runs")).toBeInTheDocument();
  });

  it("shows the empty state with a launch link when there are no runs", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([]);
    view();
    expect(
      await screen.findByText("no runs yet — launch the first evaluation to start the history"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New evaluation" })).toHaveAttribute("href", "/new");
  });

  it("surfaces a load error", async () => {
    vi.mocked(api.listRuns).mockRejectedValue(new Error("api unreachable"));
    view();
    expect(await screen.findByText("api unreachable")).toBeInTheDocument();
  });

  it("tracks selection of finished runs", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([run({ id: "a" })]);
    view();
    await screen.findByText("claude-sonnet-4");
    const box = screen.getByRole("checkbox");
    await userEvent.click(box);
    expect(box).toBeChecked();
  });

  it("hands finished selections to /compare as run: ids", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([run({ id: "a" }), run({ id: "b", model: "openai/gpt-5.2" })]);
    view();
    await screen.findByText("claude-sonnet-4");
    const boxes = screen.getAllByRole("checkbox");
    await userEvent.click(boxes[0]);
    await userEvent.click(boxes[1]);
    expect(screen.getByRole("link", { name: "Compare selected →" })).toHaveAttribute(
      "href",
      "/compare?evals=run%3Aa%2Crun%3Ab",
    );
  });

  it("keeps the compare button hidden below two selections", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([run({ id: "a" })]);
    view();
    await screen.findByText("claude-sonnet-4");
    expect(screen.queryByRole("link", { name: "Compare selected →" })).not.toBeInTheDocument();
  });

  it("exports a finished run's report as HTML from the row", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([run({ id: "a" })]);
    vi.mocked(api.getRun).mockResolvedValue({
      status: "done",
      error: null,
      report: {
        header: {
          model: "anthropic/claude-sonnet-4", engine: "llm", grader: null, org: "meridian",
          k: 5, created: "2026-08-29T14:02:11Z", location: "l", scorer_version: null,
          inspect_ai_version: null, scaffold: "baseline", seed: 0, harness: "single",
        },
        overall: { pass_k_rate: 0.72, mean_rate: 0.94 },
        categories: [], probes: [],
        axes: {
          accuracy_rate: null, provenance_rate: 1, refusal_rate: null, n_answer_epochs: 0,
          n_refuse_epochs: 0, n_total_epochs: 0, answer_format_rate: null,
        },
      },
    });
    view();
    await screen.findByText("claude-sonnet-4");
    await userEvent.click(screen.getByRole("button", { name: "HTML" }));
    expect(vi.mocked(api.getRun)).toHaveBeenCalledWith("a");
    expect(vi.mocked(downloadText)).toHaveBeenCalledWith(
      "tessera-meridian-claude-sonnet-4-2026-08-29.html",
      expect.stringContaining("<!doctype html>"),
      "text/html",
    );
  });
});
