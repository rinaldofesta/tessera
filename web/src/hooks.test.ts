import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Report } from "@/types";

vi.mock("@/api", () => ({ api: { watchRun: vi.fn(), getRun: vi.fn() } }));
import { api } from "@/api";
import { useRunStatus } from "./hooks";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

class FakeSource {
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
}

const report = { header: { k: 3 }, probes: [] } as unknown as Report;

describe("useRunStatus", () => {
  it("starts running and resolves to done with the report from the terminal fetch", async () => {
    const source = new FakeSource();
    vi.mocked(api.watchRun).mockReturnValue(source as unknown as EventSource);
    vi.mocked(api.getRun).mockResolvedValue({ status: "done", report, error: null });

    const { result } = renderHook(() => useRunStatus("abc"));
    expect(result.current.status).toBe("running");

    act(() => source.onmessage!({ data: JSON.stringify({ status: "done", error: null }) }));
    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.report).toBe(report);
    expect(source.close).toHaveBeenCalled();
  });

  it("surfaces an error status and message", async () => {
    const source = new FakeSource();
    vi.mocked(api.watchRun).mockReturnValue(source as unknown as EventSource);
    vi.mocked(api.getRun).mockResolvedValue({ status: "error", report: null, error: "boom" });

    const { result } = renderHook(() => useRunStatus("abc"));
    act(() => source.onmessage!({ data: JSON.stringify({ status: "error", error: "boom" }) }));
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error).toBe("boom");
  });

  it("closes the source on unmount", () => {
    const source = new FakeSource();
    vi.mocked(api.watchRun).mockReturnValue(source as unknown as EventSource);
    vi.mocked(api.getRun).mockResolvedValue({ status: "done", report: null, error: null });

    const { unmount } = renderHook(() => useRunStatus("abc"));
    unmount();
    expect(source.close).toHaveBeenCalled();
  });

  it("resets state when the id changes", async () => {
    const first = new FakeSource();
    const second = new FakeSource();
    vi.mocked(api.watchRun).mockReturnValueOnce(first as unknown as EventSource)
      .mockReturnValueOnce(second as unknown as EventSource);
    vi.mocked(api.getRun).mockResolvedValue({ status: "done", report, error: null });

    const { result, rerender } = renderHook(({ id }) => useRunStatus(id), {
      initialProps: { id: "a" },
    });
    act(() => first.onmessage!({ data: JSON.stringify({ status: "done", error: null }) }));
    await waitFor(() => expect(result.current.status).toBe("done"));

    rerender({ id: "b" });
    expect(result.current.status).toBe("running");
    expect(result.current.report).toBeNull();
    expect(first.close).toHaveBeenCalled();
  });
});
