import { act, cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { runFixture } from "@/test/fixtures";

vi.mock("@/api", () => ({ api: { watchRun: vi.fn(), getRun: vi.fn() } }));
import { api } from "@/api";
import { LiveRunPanel } from "./LiveRunPanel";

afterEach(() => { cleanup(); vi.clearAllMocks(); });
class FakeSource { onmessage: ((event: { data: string }) => void) | null = null; onerror: (() => void) | null = null; close = vi.fn(); }

describe("LiveRunPanel", () => {
  it("fills atomically and shows the compact server outcome", async () => {
    const source = new FakeSource();
    vi.mocked(api.watchRun).mockReturnValue(source as unknown as EventSource);
    vi.mocked(api.getRun).mockResolvedValue(runFixture());
    render(<MemoryRouter><LiveRunPanel jobId="run-1" questions={2} repeats={3} model="anthropic/test" suite="starter" /></MemoryRouter>);
    expect(screen.getByText("running…")).toBeInTheDocument();
    act(() => source.onmessage?.({ data: JSON.stringify({ status: "completed", error: null }) }));
    expect(await screen.findByText(/Right every time/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open run detail →" })).toHaveAttribute("href", "/reports/run-1");
  });
});
