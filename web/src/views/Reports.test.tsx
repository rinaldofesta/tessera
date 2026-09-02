import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { runFixture } from "@/test/fixtures";

vi.mock("@/api", () => ({ api: { catalog: vi.fn(), listRuns: vi.fn(), getRun: vi.fn(), setRunArchived: vi.fn() } }));
vi.mock("@/lib/exportReport", () => ({ downloadReport: vi.fn() }));
import { api } from "@/api";
import Reports from "./Reports";

afterEach(() => { cleanup(); vi.clearAllMocks(); });
beforeEach(() => {
  vi.mocked(api.catalog).mockResolvedValue({ defaults: { engine: "deterministic", suite: "starter", k: 3, scaffold: "baseline", seed: 0 }, suites: [], models: [], providers: [], scorers: [{ engine: "deterministic", version: "det-4" }], scaffolds: ["baseline"] });
  vi.mocked(api.listRuns).mockResolvedValue([]);
});
const view = () => render(<MemoryRouter><Reports /></MemoryRouter>);

describe("Reports", () => {
  it("filters rows by model or suite", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      runFixture({ id: "a", request: { ...runFixture().request, model: "anthropic/claude" } }),
      runFixture({ id: "b", request: { ...runFixture().request, model: "openai/gpt", suite: "meridian" } }),
    ]);
    view();
    expect(await screen.findByText("claude")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("textbox", { name: "Filter by model or suite…" }), "meridian");
    expect(screen.queryByText("claude")).not.toBeInTheDocument();
    expect(screen.getByText("gpt")).toBeInTheDocument();
  });

  it("reloads with archived reports when toggled", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([runFixture()]);
    view();
    await screen.findByText("claude-sonnet-4");
    await userEvent.click(screen.getByRole("checkbox", { name: "show archived" }));
    await waitFor(() => expect(api.listRuns).toHaveBeenCalledWith(true));
  });

  it("links the empty state to Run", async () => {
    view();
    expect(await screen.findByRole("link", { name: "Run your first" })).toHaveAttribute("href", "/");
  });

  it("does not offer Archive for bundled examples", async () => {
    vi.mocked(api.listRuns).mockResolvedValue([runFixture({ source: "bundled" })]);
    view();
    await screen.findByText(/bundled example/);
    expect(screen.queryByRole("button", { name: "Archive" })).not.toBeInTheDocument();
  });
});
