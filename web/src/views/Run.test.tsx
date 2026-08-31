import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/api", () => ({
  api: {
    evalSetup: vi.fn(),
    startRun: vi.fn(),
    listRuns: vi.fn().mockResolvedValue([]),
    rescan: vi.fn(),
    watchRun: vi.fn(),
    getRun: vi.fn(),
  },
}));
import { api } from "@/api";
import Run from "./Run";

afterEach(cleanup);

class FakeSource {
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
}

beforeEach(() => {
  vi.mocked(api.evalSetup).mockResolvedValue({
    defaults: { engine: "deterministic", repeats: 3 },
    models: [
      { id: "x/a", label: "A", provider: "x", readiness: "ready", source: "s", published: true, released: null, retired: null },
    ],
    suites: [{ id: "toy", kind: "builtin", questions: 4 }],
    sources: [],
  } as never);
  vi.mocked(api.watchRun).mockReturnValue(new FakeSource() as unknown as EventSource);
});

function LocationDisplay() {
  return <output data-testid="location-display">{useLocation().pathname}</output>;
}

const view = () => render(
  <MemoryRouter initialEntries={["/new"]}>
    <LocationDisplay />
    <Routes>
      <Route path="/new" element={<Run />} />
      <Route path="*" element={<div>navigated away</div>} />
    </Routes>
  </MemoryRouter>,
);

describe("Run — launch left, watch right", () => {
  it("previews what will run before launch, mosaic pending", async () => {
    view();
    expect(await screen.findByText("what will run")).toBeInTheDocument();
    expect(screen.getByText(/12 answers/)).toBeInTheDocument();
  });

  it("stays on /new and flips the panel live on launch", async () => {
    vi.mocked(api.startRun).mockResolvedValue({ job_id: "job1", status: "running" } as never);
    view();
    await screen.findByText("what will run");
    await userEvent.click(screen.getByRole("radio", { name: /Toy starter/ }));
    await userEvent.click(screen.getByRole("button", { name: "Continue — choose the model" }));
    await userEvent.click(await screen.findByRole("radio", { name: /A/ }));
    await userEvent.click(screen.getByRole("button", { name: "Continue — confirm & launch" }));
    await userEvent.click(await screen.findByRole("button", { name: "Run evaluation" }));
    expect(await screen.findByText(/live — a on toy|live — x\/a on toy/i)).toBeInTheDocument();
    expect(screen.getByText("running…")).toBeInTheDocument();
    expect(api.startRun).toHaveBeenCalled();
    expect(screen.getByTestId("location-display")).toHaveTextContent("/new");
  });
});
