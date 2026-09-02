import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { comparisonFixture, runFixture } from "@/test/fixtures";

vi.mock("@/api", () => ({ api: { getRun: vi.fn(), compareRuns: vi.fn() } }));
import { api } from "@/api";
import { ComparePanel } from "./ComparePanel";

afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("ComparePanel", () => {
  it("renders two category series and treats incompatibility as a warning", async () => {
    vi.mocked(api.getRun).mockResolvedValue(runFixture({ id: "b", request: { ...runFixture().request, model: "openai/gpt-4o" } }));
    vi.mocked(api.compareRuns).mockResolvedValue(comparisonFixture);
    const { container } = render(<ComparePanel run={runFixture()} vs="b" />);
    expect(await screen.findByText("protocol differs")).toBeInTheDocument();
    expect(screen.getByText("grader")).toBeInTheDocument();
    expect(container.querySelectorAll("[data-bar]")).toHaveLength(4);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders a 409 as a plain line", async () => {
    vi.mocked(api.getRun).mockResolvedValue(runFixture({ id: "b" }));
    vi.mocked(api.compareRuns).mockRejectedValue(new Error("Both reports must be completed (409)"));
    render(<ComparePanel run={runFixture()} vs="b" />);
    expect(await screen.findByText(/Both reports must be completed/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
