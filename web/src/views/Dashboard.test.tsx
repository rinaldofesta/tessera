import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api";
import type { RunSummary } from "@/types";
import Dashboard from "./Dashboard";

vi.mock("@/api", () => ({ api: { listRuns: vi.fn(), trends: vi.fn() } }));

vi.stubGlobal("ResizeObserver", class {
  observe() {}
  unobserve() {}
  disconnect() {}
});

afterEach(cleanup);

const run = (overrides: Partial<RunSummary> = {}): RunSummary => ({
  id: "run-1", status: "done", error: null, model: "openai/gpt-5.2", org: "meridian",
  judge: "llm", grader: "anthropic/claude-sonnet-4", epochs: 5,
  created_at: "2026-08-29T14:02:11Z", finished_at: "2026-08-29T14:31:40Z",
  pass_k_rate: 0.72, mean_rate: 0.94, archived: false, ...overrides,
});

const renderDashboard = () => render(<MemoryRouter><Dashboard /></MemoryRouter>);

describe("Dashboard", () => {
  it("shows the latest pass^k and mean tiles", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([run()]);
    vi.mocked(api.trends).mockResolvedValue([]);
    renderDashboard();
    await waitFor(() => expect(screen.getAllByText("72%").length).toBeGreaterThan(0));
    expect(screen.getAllByText("94%").length).toBeGreaterThan(0);
  });

  it("shows the empty-state CTA linked to the launcher", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([]);
    vi.mocked(api.trends).mockResolvedValue([]);
    renderDashboard();
    expect(await screen.findByText("no runs recorded yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Run the first eval" })).toHaveAttribute("href", "/new");
  });

  it("renders recent RunRows without selection controls", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([run()]);
    vi.mocked(api.trends).mockResolvedValue([]);
    renderDashboard();
    expect(await screen.findByText("gpt-5.2")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("shows the trend section for two or more points", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([run()]);
    vi.mocked(api.trends).mockResolvedValue([
      { pass_k_rate: 0.72, mean_rate: 0.94 },
      { pass_k_rate: 0.8, mean_rate: 0.96 },
    ] as never);
    renderDashboard();
    expect(await screen.findByText("the gap over time")).toBeInTheDocument();
  });
});
