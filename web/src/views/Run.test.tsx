import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Catalog, Plan, RunSpec } from "@/types";
import { runFixture } from "@/test/fixtures";

vi.mock("@/api", () => ({ api: { catalog: vi.fn(), dryRun: vi.fn(), startRun: vi.fn(), watchRun: vi.fn(), getRun: vi.fn(), saveProvider: vi.fn() } }));
import { api } from "@/api";
import Run from "./Run";

const catalog: Catalog = {
  defaults: { engine: "deterministic", suite: "starter", k: 3, scaffold: "baseline", seed: 0 },
  suites: [{ name: "starter", label: "Starter", org: "starter", kind: "builtin", questions: 2, claims: 4, editable: false }],
  models: [{ id: "x/model", label: "Model", provider: "x", connected: true }],
  providers: [{ id: "x", label: "Provider X", connected: true, fields: [{ id: "api_key", env_var: "X_KEY" }] }],
  scorers: [{ engine: "deterministic", version: "det-4" }], scaffolds: ["baseline"],
};
const ready = (request: RunSpec = runFixture().request): Plan => ({ blockers: [], diagnostics: [], provider: "x", ready: true, request: { ...request, grader: request.grader ?? null }, scorer_version: "det-4", suite: catalog.suites[0] });

afterEach(() => { cleanup(); vi.clearAllMocks(); });
beforeEach(() => {
  vi.mocked(api.catalog).mockResolvedValue(catalog);
  vi.mocked(api.dryRun).mockImplementation(async (spec) => ready(spec));
  vi.mocked(api.startRun).mockResolvedValue(runFixture({ status: "queued", report: null, verdict: null }));
  vi.mocked(api.watchRun).mockReturnValue({ close: vi.fn(), onmessage: null, onerror: null } as unknown as EventSource);
});

describe("Run readiness", () => {
  it("initializes from rerun query params and gates launch on the server Plan", async () => {
    render(<MemoryRouter initialEntries={["/?model=x%2Fmodel&suite=starter&k=2&engine=deterministic&grader=&scaffold=baseline&seed=4"]}><Run /></MemoryRouter>);
    expect(await screen.findByRole("combobox", { name: "times each" })).toHaveValue("2");
    await waitFor(() => expect(api.dryRun).toHaveBeenCalledWith(expect.objectContaining({ model: "x/model", k: 2, seed: 4 })));
    expect(await screen.findByRole("button", { name: "Run" })).toBeEnabled();
  });

  it("renders blockers and a connect card from the dry-run response", async () => {
    vi.mocked(api.dryRun).mockResolvedValue({ ...ready(), ready: false, blockers: [{ code: "not_connected", message: "Provider X needs a key.", fix: "connect" }] });
    render(<MemoryRouter><Run /></MemoryRouter>);
    expect(await screen.findByText("Provider X needs a key.")).toBeInTheDocument();
    expect(screen.getByLabelText("API key — Provider X")).toHaveAttribute("type", "password");
    expect(screen.queryByRole("button", { name: "Run" })).not.toBeInTheDocument();
  });

  it("launches with the planned spec", async () => {
    render(<MemoryRouter><Run /></MemoryRouter>);
    const button = await screen.findByRole("button", { name: "Run" });
    await waitFor(() => expect(button).toBeEnabled());
    await userEvent.click(button);
    expect(api.startRun).toHaveBeenCalledWith(expect.objectContaining({ model: "x/model", suite: "starter" }));
  });
});
