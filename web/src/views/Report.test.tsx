import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { runFixture } from "@/test/fixtures";

vi.mock("@/api", () => ({ api: { catalog: vi.fn(), getRun: vi.fn(), watchRun: vi.fn(), listRuns: vi.fn(), setRunArchived: vi.fn(), compareRuns: vi.fn() } }));
vi.mock("@/lib/exportReport", () => ({ downloadReport: vi.fn(), exportReportHtml: vi.fn() }));
import { api } from "@/api";
import { downloadReport } from "@/lib/exportReport";
import Report from "./Report";

class FakeSource { onmessage: ((event: { data: string }) => void) | null = null; onerror: (() => void) | null = null; close = vi.fn(); }
const view = (entry = "/reports/run-1") => render(<MemoryRouter initialEntries={[entry]}><Routes><Route path="/reports/:id" element={<Report />} /></Routes></MemoryRouter>);

afterEach(() => { cleanup(); vi.clearAllMocks(); });
beforeEach(() => {
  vi.mocked(api.catalog).mockResolvedValue({ defaults: { engine: "deterministic", suite: "starter", k: 3, scaffold: "baseline", seed: 0 }, suites: [{ name: "starter", label: "Starter", org: "starter", kind: "builtin", questions: 2, claims: 4, editable: false }], models: [], providers: [], scorers: [], scaffolds: ["baseline"] });
  vi.mocked(api.getRun).mockResolvedValue(runFixture());
  vi.mocked(api.watchRun).mockReturnValue(new FakeSource() as unknown as EventSource);
  vi.mocked(api.listRuns).mockResolvedValue([]);
});

describe("Report", () => {
  it("renders the server sentence, mosaic and three-word gap legend", async () => {
    view();
    expect(await screen.findByRole("heading", { name: "Not reliable." })).toBeInTheDocument();
    expect(screen.getByText("Right every time on 1 of 2 questions.")).toBeInTheDocument();
    const mosaic = screen.getByRole("img", { name: "Answer grid: 2 questions by 3 repeats" });
    expect(mosaic.querySelectorAll("span")).toHaveLength(6);
    expect(screen.getByText(/right every time 50%/)).toBeInTheDocument();
    expect(screen.getByText(/only sometimes/)).toBeInTheDocument();
    expect(screen.getByText("never")).toBeInTheDocument();
  });

  it("keeps Details closed by default and opens it for #details", async () => {
    const first = view();
    const details = (await screen.findByText("Details")).closest("details")!;
    expect(details).not.toHaveAttribute("open");
    first.unmount();
    view("/reports/run-1#details");
    expect((await screen.findByText("Details")).closest("details")).toHaveAttribute("open");
  });

  it("saves HTML and copies the exact three-line summary", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    view();
    await userEvent.click(await screen.findByRole("button", { name: "Save report" }));
    expect(downloadReport).toHaveBeenCalledWith(expect.objectContaining({ id: "run-1" }), "html");
    await userEvent.click(screen.getByRole("button", { name: "Copy summary" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    expect(writeText.mock.calls[0][0].split("\n")).toHaveLength(3);
  });

  it("hides Archive for bundled reports", async () => {
    vi.mocked(api.getRun).mockResolvedValue(runFixture({ source: "bundled" }));
    view();
    await screen.findByText("Not reliable.");
    expect(screen.queryByRole("button", { name: "Archive" })).not.toBeInTheDocument();
  });

  it("shows the live panel for a queued run", async () => {
    vi.mocked(api.getRun).mockResolvedValue(runFixture({ status: "queued", report: null, verdict: null, receipt: null }));
    view();
    expect(await screen.findByText(/live —/)).toBeInTheDocument();
    expect(screen.getByText("running…")).toBeInTheDocument();
  });
});
