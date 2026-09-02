import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/api", () => ({
  api: {
    evalSetup: vi.fn().mockResolvedValue({
      defaults: { engine: "deterministic", repeats: 3 },
      models: [
        { id: "x/a", label: "A", provider: "x", readiness: "ready", source: "s", published: true, released: null, retired: null },
        { id: "x/b", label: "B", provider: "x", readiness: "ready", source: "s", published: true, released: null, retired: null },
      ],
      suites: [{ id: "toy", questions: 4 }],
      sources: [],
    }),
    listExperiments: vi.fn().mockResolvedValue([]),
    preflight: vi.fn(),
    startExperiment: vi.fn(),
    resumeExperiment: vi.fn(),
    compareExperiment: vi.fn(),
  },
}));
import ExperimentsTab from "./ExperimentsTab";

afterEach(cleanup);

describe("ExperimentsTab", () => {
  it("renders the create form and the empty experiments list", async () => {
    render(<MemoryRouter><ExperimentsTab /></MemoryRouter>);
    expect(await screen.findByText("new controlled experiment")).toBeInTheDocument();
    expect(screen.getByText("no experiments yet")).toBeInTheDocument();
  });
});
