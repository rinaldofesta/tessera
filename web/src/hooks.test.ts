import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Catalog } from "@/types";
import { runFixture } from "@/test/fixtures";

vi.mock("@/api", () => ({ api: { catalog: vi.fn(), watchRun: vi.fn(), getRun: vi.fn() } }));
import { api } from "@/api";
import { useCatalog, useRunStatus } from "./hooks";

afterEach(() => { cleanup(); vi.clearAllMocks(); });

class FakeSource {
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
}

const catalog = { defaults: { engine: "deterministic", suite: "starter", k: 3, scaffold: "baseline", seed: 0 }, suites: [], models: [], providers: [], scorers: [], scaffolds: ["baseline"] } as Catalog;

describe("shared catalog", () => {
  it("fetches once for multiple consumers", async () => {
    vi.mocked(api.catalog).mockResolvedValue(catalog);
    const { result } = renderHook(() => ({ first: useCatalog(), second: useCatalog() }));
    await waitFor(() => expect(result.current.first.catalog).toBe(catalog));
    expect(api.catalog).toHaveBeenCalledOnce();
  });
});

describe("useRunStatus", () => {
  it("refetches the full Run when the stream becomes terminal", async () => {
    const source = new FakeSource();
    const completed = runFixture();
    vi.mocked(api.watchRun).mockReturnValue(source as unknown as EventSource);
    vi.mocked(api.getRun).mockResolvedValue(completed);
    const { result } = renderHook(() => useRunStatus("run-1"));
    expect(result.current.terminal).toBe(false);
    act(() => source.onmessage?.({ data: JSON.stringify({ status: "completed", error: null }) }));
    await waitFor(() => expect(result.current.run).toBe(completed));
    expect(result.current.terminal).toBe(true);
    expect(source.close).toHaveBeenCalled();
  });

  it("surfaces terminal failure text", async () => {
    const source = new FakeSource();
    vi.mocked(api.watchRun).mockReturnValue(source as unknown as EventSource);
    vi.mocked(api.getRun).mockResolvedValue(runFixture({ status: "failed", report: null, verdict: null, error: "boom" }));
    const { result } = renderHook(() => useRunStatus("run-1"));
    act(() => source.onmessage?.({ data: JSON.stringify({ status: "failed", error: "boom" }) }));
    await waitFor(() => expect(result.current.terminal).toBe(true));
    expect(result.current.error).toBe("boom");
  });
});
