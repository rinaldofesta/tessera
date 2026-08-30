import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GapBar } from "./GapBar";

const seg = (c: HTMLElement, name: string) =>
  c.querySelector<HTMLElement>(`[data-seg="${name}"]`)!;

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("GapBar", () => {
  it("splits fill and hatched gap at the two rates", () => {
    const { container, getByRole } = render(<GapBar passK={0.72} mean={0.94} k={5} />);
    expect(seg(container, "pass").style.width).toBe("72%");
    expect(seg(container, "gap").style.width).toBe("22%");
    expect(getByRole("img").getAttribute("aria-label")).toBe(
      "72% reliable (pass^5), 94% mean success, 22 point gap",
    );
  });

  it("shows zero gap when pass^k equals the mean", () => {
    const { container, getByRole } = render(<GapBar passK={0.5} mean={0.5} k={3} />);
    expect(seg(container, "gap").style.width).toBe("0%");
    expect(getByRole("img").getAttribute("aria-label")).toContain("0 point gap");
  });

  it("renders the all-pass state green at exactly 1", () => {
    const { container } = render(<GapBar passK={1} mean={1} k={3} />);
    expect(seg(container, "pass").className).toMatch(/verdict-reliable/);
    expect(seg(container, "pass").style.width).toBe("100%");
  });

  it("uses iris, not green, below 1", () => {
    const { container } = render(<GapBar passK={0.99} mean={1} k={3} />);
    expect(seg(container, "pass").className).not.toMatch(/verdict-reliable/);
  });

  it("renders an empty bar at zero", () => {
    const { container } = render(<GapBar passK={0} mean={0} k={3} />);
    expect(seg(container, "pass").style.width).toBe("0%");
    expect(seg(container, "gap").style.width).toBe("0%");
  });

  it("clamps inconsistent inputs (passK > mean) to a zero gap and warns", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { container } = render(<GapBar passK={0.9} mean={0.8} k={3} />);
    expect(seg(container, "gap").style.width).toBe("0%");
    expect(warn).toHaveBeenCalledOnce();
  });
});
