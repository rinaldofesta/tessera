import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api";
import type { Catalog, Provider, Run as ApiRun } from "@/types";

vi.mock("@/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/api")>();
  return {
    ...original,
    api: {
      catalog: vi.fn(), saveProvider: vi.fn(), startRun: vi.fn(),
      listRuns: vi.fn().mockResolvedValue([]), watchRun: vi.fn(), getRun: vi.fn(),
    },
  };
});
import { api } from "@/api";
import Run from "./Run";

const catalog: Catalog = {
  defaults: { engine: "deterministic", suite: "starter", k: 4, scaffold: "strict", seed: 7 },
  suites: [
    { name: "starter", label: "Starter — 4 questions", org: "toy", kind: "builtin", questions: 4, claims: 8, editable: false },
    { name: "meridian", label: "Meridian — 22 questions", org: "meridian", kind: "builtin", questions: 22, claims: 30, editable: false },
  ],
  models: [
    { id: "x/a", label: "Model A", provider: "x", connected: true },
    { id: "x/b", label: "Model B", provider: "x", connected: true },
    { id: "y/c", label: "Model C", provider: "y", connected: false },
  ],
  providers: [
    { id: "x", label: "Provider X", connected: true, fields: [{ id: "api_key", env_var: "X_API_KEY" }] },
    { id: "y", label: "Provider Y", connected: false, fields: [{ id: "api_key", env_var: "Y_API_KEY" }] },
  ],
  scorers: [{ engine: "deterministic", version: "det-4" }],
  scaffolds: ["baseline", "strict"],
};

const providerDetails = [
  { id: "x", configured: true, fields: [{ id: "api_key", env_var: "X_API_KEY", configured: true }] },
  { id: "y", configured: false, fields: [{ id: "api_key", env_var: "Y_API_KEY", configured: false }] },
] as unknown as Provider[];

function run(id = "job-1"): ApiRun {
  return {
    ok: true, id, status: "queued", source: "run", archived: false, schema_version: 1,
    created_at: "2026-09-02T10:00:00Z", started_at: null, finished_at: null,
    request: { suite: "starter", model: "x/a", engine: "deterministic", grader: null, k: 4, scaffold: "strict", seed: 7 },
    verdict: null, gate: null, report: null, receipt: null, diagnostics: [],
    paths: { dir: `/runs/${id}`, log: null, report_json: null, report_md: null }, error: null,
  };
}

class FakeSource {
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
}

function LocationDisplay() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}

function view() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <LocationDisplay />
      <Routes>
        <Route path="/" element={<Run />} />
        <Route path="/suites" element={<div>suite editor</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  vi.mocked(api.catalog).mockResolvedValue(catalog);
  vi.mocked(api.listRuns).mockResolvedValue([]);
  vi.mocked(api.watchRun).mockReturnValue(new FakeSource() as unknown as EventSource);
});

describe("Run sentence", () => {
  it("applies every catalog default and previews the pending mosaic", async () => {
    view();
    expect(await screen.findByText("Ask")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "model" })).toHaveValue("x/a");
    expect(screen.getByRole("combobox", { name: "suite" })).toHaveValue("starter");
    expect(screen.getByRole("combobox", { name: "times each" })).toHaveValue("4");
    expect(screen.getByText("pending · 4 questions × 4 repeats")).toBeInTheDocument();

    await userEvent.click(screen.getByText(/Advanced/));
    expect(screen.getByRole("radio", { name: "deterministic" })).toBeChecked();
    expect(screen.getByLabelText("scaffold")).toHaveValue("strict");
    expect(screen.getByLabelText("seed")).toHaveValue(7);
  });

  it("posts the edited suite, model, and k as a RunSpec", async () => {
    vi.mocked(api.startRun).mockResolvedValue(run());
    view();
    await screen.findByText("Ask");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "model" }), "x/b");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "suite" }), "meridian");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "times each" }), "2");
    await userEvent.click(screen.getByRole("button", { name: "Run" }));

    expect(api.startRun).toHaveBeenCalledWith({
      model: "x/b", suite: "meridian", engine: "deterministic", grader: null,
      k: 2, scaffold: "strict", seed: 7,
    });
  });

  it("launches once, stays on the page, disables Run, and opens the live panel", async () => {
    let resolveRun!: (value: ApiRun) => void;
    vi.mocked(api.startRun).mockReturnValue(new Promise((resolve) => { resolveRun = resolve; }));
    view();
    await screen.findByText("Ask");
    const button = screen.getByRole("button", { name: "Run" });
    await userEvent.click(button);
    expect(screen.getByRole("button", { name: "Starting…" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Starting…" }));
    expect(api.startRun).toHaveBeenCalledTimes(1);

    resolveRun(run("live-1"));
    expect(await screen.findByText(/live —/i)).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/");
    expect(screen.getByRole("button", { name: "Run" })).toBeDisabled();
  });

  it("renders every 422 blocker and shows ConnectCard for not_connected", async () => {
    vi.mocked(api.startRun).mockRejectedValue(new ApiError("blocked", 422, [
      { code: "not_connected", message: "Provider X needs a key.", fix: "connect" },
      { code: "unknown_suite", message: "The suite is gone.", fix: null },
    ]));
    view();
    await screen.findByText("Ask");
    await userEvent.click(screen.getByRole("button", { name: "Run" }));
    expect(await screen.findByText("Provider X needs a key.")).toBeInTheDocument();
    expect(screen.getByText("The suite is gone.")).toBeInTheDocument();
    expect(screen.getByLabelText("API key — Provider X")).toHaveAttribute("type", "password");
    expect(screen.queryByRole("button", { name: "Run" })).not.toBeInTheDocument();
  });

  it("shows ConnectCard instead of Run when the selected provider is disconnected", async () => {
    view();
    await screen.findByText("Ask");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "model" }), "y/c");
    expect(screen.getByLabelText("API key — Provider Y")).toHaveAttribute("title", "Y_API_KEY");
    expect(screen.queryByRole("button", { name: "Run" })).not.toBeInTheDocument();
  });

  it("saves a missing key, reloads the catalog, and restores Run without retaining it", async () => {
    const connectedCatalog: Catalog = {
      ...catalog,
      models: catalog.models.map((model) => (
        model.provider === "y" ? { ...model, connected: true } : model
      )),
      providers: catalog.providers.map((provider) => (
        provider.id === "y" ? { ...provider, connected: true } : provider
      )),
    };
    vi.mocked(api.catalog).mockResolvedValueOnce(catalog).mockResolvedValue(connectedCatalog);
    vi.mocked(api.saveProvider).mockResolvedValue(providerDetails[1]);
    view();
    await screen.findByText("Ask");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "model" }), "y/c");
    const input = screen.getByLabelText("API key — Provider Y");
    await userEvent.type(input, "secret-value");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(api.saveProvider).toHaveBeenCalledWith("y", { api_key: "secret-value" });
    expect(await screen.findByRole("button", { name: "Run" })).toBeInTheDocument();
    expect(api.catalog).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("secret-value")).not.toBeInTheDocument();
    expect(screen.queryByText("Y_API_KEY")).not.toBeInTheDocument();
  });

  it("navigates the final suite option to /suites", async () => {
    view();
    await screen.findByText("Ask");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "suite" }), "__custom_suite__");
    expect(await screen.findByText("suite editor")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/suites");
  });
});
