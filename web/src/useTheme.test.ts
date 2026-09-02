import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useTheme } from "./hooks";

type ChangeListener = () => void;

let dark = false;
const listeners = new Set<ChangeListener>();

// An explicit in-memory stub, not jsdom's own `localStorage` — the host Node runtime's
// experimental native Web Storage global can shadow or conflict with jsdom's per-test
// implementation (observed nondeterministically on Node 24+), so this keeps the test
// deterministic regardless of which Node version runs it.
function fakeLocalStorage() {
  const store = new Map<string, string>();
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => { store.set(key, value); },
    removeItem: (key: string) => { store.delete(key); },
    clear: () => { store.clear(); },
  };
}

beforeEach(() => {
  vi.stubGlobal("localStorage", fakeLocalStorage());
  dark = false;
  listeners.clear();
  vi.stubGlobal("matchMedia", vi.fn(() => ({
    get matches() { return dark; },
    media: "(prefers-color-scheme: dark)",
    onchange: null,
    addEventListener: (_type: string, listener: ChangeListener) => listeners.add(listener),
    removeEventListener: (_type: string, listener: ChangeListener) => listeners.delete(listener),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  delete document.documentElement.dataset.theme;
});

describe("useTheme", () => {
  it("persists and applies an explicit theme", async () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("dark"));
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
    expect(localStorage.getItem("tessera.theme")).toBe("dark");
  });

  it("restores a persisted theme and cycles system → light → dark", async () => {
    localStorage.setItem("tessera.theme", "system");
    const { result } = renderHook(() => useTheme());
    act(() => result.current.cycleTheme());
    expect(result.current.theme).toBe("light");
    act(() => result.current.cycleTheme());
    expect(result.current.theme).toBe("dark");
    await waitFor(() => expect(localStorage.getItem("tessera.theme")).toBe("dark"));
  });

  it("follows media-query changes in system mode", async () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("system");
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
    act(() => {
      dark = true;
      listeners.forEach((listener) => listener());
    });
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
