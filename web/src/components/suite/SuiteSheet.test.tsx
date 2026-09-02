import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Blueprint, Catalog, Plan, RunSpec } from "@/types";
import { runFixture } from "@/test/fixtures";

vi.mock("@/api", () => ({
  api: {
    catalog: vi.fn(),
    dryRun: vi.fn(),
    startRun: vi.fn(),
    watchRun: vi.fn(),
    getRun: vi.fn(),
    saveProvider: vi.fn(),
    getBlueprint: vi.fn(),
    validateBlueprint: vi.fn(),
    previewBlueprint: vi.fn(),
    createBlueprint: vi.fn(),
    saveBlueprint: vi.fn(),
    deleteBlueprint: vi.fn(),
  },
}));
import { api } from "@/api";
import Run from "@/views/Run";
import { SuiteSheet } from "./SuiteSheet";

const blueprint: Blueprint = {
  claims: [{
    claim_id: "acme__tier__crm",
    subject: "Acme",
    predicate: "tier",
    value: "Gold",
    silo: "crm",
    render: { as: "field" },
  }],
  probes: [{
    probe_id: "q__acme__tier",
    question: "What is Acme's tier?",
    references: ["acme__tier__crm"],
    conflict_type: "none",
    expected_behavior: "answer",
    expected_answer: "Gold",
    expected_sources: ["acme__tier__crm"],
  }],
};

const builtin = { name: "starter", label: "Starter", org: "toy", kind: "builtin" as const, questions: 1, claims: 1, editable: false };
const userSuite = { name: "customer-care", label: "customer-care", org: "customer-care", kind: "user" as const, questions: 1, claims: 1, editable: true };
let catalog: Catalog;

function ready(request: RunSpec): Plan {
  return { blockers: [], diagnostics: [], provider: "x", ready: true, request, scorer_version: "det-4", suite: catalog.suites[0] };
}

function renderSheet(path = "/?edit=new", onSaved = vi.fn()) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <SuiteSheet onSaved={onSaved} />
    </MemoryRouter>,
  );
}

afterEach(() => { cleanup(); vi.clearAllMocks(); });
beforeEach(() => {
  catalog = {
    defaults: { engine: "deterministic", suite: "starter", k: 3, scaffold: "baseline", seed: 0 },
    suites: [builtin, userSuite],
    models: [{ id: "x/model", label: "Model", provider: "x", connected: true }],
    providers: [{ id: "x", label: "Provider X", connected: true, fields: [{ id: "api_key", env_var: "X_KEY" }] }],
    scorers: [{ engine: "deterministic", version: "det-4" }],
    scaffolds: ["baseline"],
  };
  vi.mocked(api.catalog).mockImplementation(async () => catalog);
  vi.mocked(api.getBlueprint).mockResolvedValue(blueprint);
  vi.mocked(api.validateBlueprint).mockResolvedValue({ ok: true, errors: [] });
  vi.mocked(api.previewBlueprint).mockResolvedValue({ manifest: {}, silos: { crm: {} }, docs: [] });
  vi.mocked(api.createBlueprint).mockResolvedValue({ id: "acme-support" });
  vi.mocked(api.saveBlueprint).mockResolvedValue({ id: "customer-care" });
  vi.mocked(api.deleteBlueprint).mockResolvedValue({ deleted: "customer-care" });
  vi.mocked(api.dryRun).mockImplementation(async (request) => ready(request));
  vi.mocked(api.startRun).mockResolvedValue(runFixture());
  vi.mocked(api.watchRun).mockReturnValue({ close: vi.fn(), onmessage: null, onerror: null } as unknown as EventSource);
});

describe("SuiteSheet", () => {
  it("opens from ?edit=new and validates names", async () => {
    renderSheet();
    expect(await screen.findByRole("dialog", { name: "Make your own suite" })).toBeInTheDocument();
    expect(screen.getByText("Enter a suite name.")).toBeInTheDocument();

    const name = screen.getByLabelText("suite name");
    await userEvent.type(name, "bad name");
    expect(screen.getByText("Start with a letter or digit and use only letters, digits, - or _.")).toBeInTheDocument();
    await userEvent.clear(name);
    await userEvent.type(name, "starter");
    expect(screen.getByText("That name is reserved for a built-in suite or alias.")).toBeInTheDocument();

    // "new" is the ?edit=new sentinel — a suite actually named "new" would be
    // indistinguishable from "start a fresh draft" and unreachable afterward.
    await userEvent.clear(name);
    await userEvent.type(name, "new");
    expect(screen.getByText("That name is reserved for a built-in suite or alias.")).toBeInTheDocument();
  });

  it("validates the blueprint after a recipe is filled", async () => {
    renderSheet();
    await screen.findByRole("dialog", { name: "Make your own suite" });
    await userEvent.click(screen.getAllByRole("button", { name: "+ new scenario" })[0]);
    await userEvent.click(await screen.findByRole("button", { name: /sources agree/i }));
    await userEvent.type(screen.getByLabelText("who or what is this about"), "Acme Corp");
    await userEvent.type(screen.getByLabelText("field name in the crm"), "tier");
    await userEvent.type(screen.getByLabelText("its value in the crm"), "Gold");
    await userEvent.type(screen.getByLabelText("what the docs page describes"), "sla_hours");
    await userEvent.type(screen.getByLabelText("the value written in the docs"), "4");
    await userEvent.click(screen.getByRole("button", { name: "next" }));

    await waitFor(() => expect(vi.mocked(api.validateBlueprint).mock.calls.some(
      ([candidate]) => (candidate.probes ?? []).some((probe) => probe.conflict_type === "none"),
    )).toBe(true));
  });

  it("posts a new suite, reloads the catalog and selects it in Run", async () => {
    vi.mocked(api.createBlueprint).mockImplementation(async (id, next) => {
      catalog = {
        ...catalog,
        suites: [...catalog.suites, { name: id, label: id, org: id, kind: "user", questions: next.probes?.length ?? 0, claims: next.claims.length, editable: true }],
      };
      return { id };
    });
    // Start from a duplicate of the built-in so the draft has questions — an empty suite cannot be saved.
    render(<MemoryRouter initialEntries={["/?edit=starter"]}><Run /></MemoryRouter>);
    await userEvent.click(await screen.findByRole("button", { name: "Duplicate as my suite" }));
    await userEvent.type(await screen.findByLabelText("suite name"), "acme-support");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(api.createBlueprint).toHaveBeenCalledWith("acme-support", expect.any(Object)));
    const select = await screen.findByRole("combobox", { name: "suite" });
    await waitFor(() => expect(within(select).getByRole("option", { name: "acme-support" })).toBeInTheDocument());
    expect(select).toHaveValue("acme-support");
  });

  it("cannot save a suite with no questions", async () => {
    renderSheet("/?edit=new");
    await userEvent.type(await screen.findByLabelText("suite name"), "acme-support");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(api.createBlueprint).not.toHaveBeenCalled();
  });

  it("shows only the duplicate action for a built-in suite", async () => {
    renderSheet("/?edit=starter");
    expect(await screen.findByRole("button", { name: "Duplicate as my suite" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });

  it("asks before deleting a user suite", async () => {
    renderSheet("/?edit=customer-care");
    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    expect(await screen.findByText("Delete 'customer-care'?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Delete suite" }));
    await waitFor(() => expect(api.deleteBlueprint).toHaveBeenCalledWith("customer-care"));
  });

  it("shows the user-owned suite path in the footer", async () => {
    renderSheet("/?edit=customer-care");
    expect(await screen.findByText(/~\/\.tessera\/suites\/customer-care\.json/)).toHaveTextContent("edit it in any editor");
  });

  it("asks before discarding an unsaved scenario when switching suites", async () => {
    renderSheet();
    await screen.findByRole("dialog", { name: "Make your own suite" });
    await userEvent.click(screen.getAllByRole("button", { name: "+ new scenario" })[0]);
    await userEvent.click(await screen.findByRole("button", { name: /sources agree/i }));
    await userEvent.type(screen.getByLabelText("who or what is this about"), "Acme Corp");
    await userEvent.type(screen.getByLabelText("field name in the crm"), "tier");
    await userEvent.type(screen.getByLabelText("its value in the crm"), "Gold");
    await userEvent.type(screen.getByLabelText("what the docs page describes"), "sla_hours");
    await userEvent.type(screen.getByLabelText("the value written in the docs"), "4");
    await userEvent.click(screen.getByRole("button", { name: "next" }));
    await userEvent.click(await screen.findByRole("button", { name: "insert" }));
    expect(await screen.findByText(/scenarios \[1\]/)).toBeInTheDocument();

    // switching suites now should ask first instead of silently discarding the insert
    await userEvent.click(screen.getByRole("button", { name: "customer-care" }));
    expect(await screen.findByText("Discard unsaved changes?")).toBeInTheDocument();

    // canceling keeps the draft and the sheet on "new"
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByText("Discard unsaved changes?")).not.toBeInTheDocument();
    expect(screen.getByText(/scenarios \[1\]/)).toBeInTheDocument();
  });

  it("falls back to the default suite in Run when the selected suite is deleted", async () => {
    vi.mocked(api.deleteBlueprint).mockImplementation(async (id) => {
      catalog = { ...catalog, suites: catalog.suites.filter((s) => s.name !== id) };
      return { deleted: id };
    });
    render(<MemoryRouter initialEntries={["/?suite=customer-care&edit=customer-care"]}><Run /></MemoryRouter>);
    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    await userEvent.click(await screen.findByRole("button", { name: "Delete suite" }));

    const select = await screen.findByRole("combobox", { name: "suite" });
    await waitFor(() => expect(select).toHaveValue("starter"));
  });
});
