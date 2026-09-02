import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";
import { VerdictBadge, verdictOf } from "./VerdictBadge";

describe("StatusBadge", () => {
  it("names each lifecycle state", () => {
    const { rerender } = render(<StatusBadge status="running" />);
    expect(screen.getByText("running…")).toBeInTheDocument();
    rerender(<StatusBadge status="completed" />);
    expect(screen.getByText("finished")).toBeInTheDocument();
    rerender(<StatusBadge status="failed" />);
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("uses no verdict color classes", () => {
    const { container, rerender } = render(<StatusBadge status="running" />);
    const className = () => container.querySelector<HTMLElement>('[data-slot="badge"]')!.className;
    expect(className()).not.toMatch(/verdict-/);
    rerender(<StatusBadge status="completed" />);
    expect(className()).not.toMatch(/verdict-/);
    rerender(<StatusBadge status="failed" />);
    expect(className()).not.toMatch(/verdict-/);
  });
});

describe("verdictOf", () => {
  it("is reliable only at pass^k = 1", () => {
    expect(verdictOf(1, 1)).toBe("reliable");
  });
  it("is inconsistent when the mean exceeds pass^k", () => {
    expect(verdictOf(0.7, 0.9)).toBe("inconsistent");
  });
  it("is unreliable when failures are consistent (mean = pass^k < 1)", () => {
    expect(verdictOf(0.5, 0.5)).toBe("unreliable");
  });
});

describe("VerdictBadge", () => {
  it("renders the verdict label", () => {
    render(<VerdictBadge verdict="inconsistent" />);
    expect(screen.getByText("inconsistent")).toBeInTheDocument();
  });
});

describe("VerdictBadge in light mode", () => {
  afterEach(() => { delete document.documentElement.dataset.theme; });

  it("keeps verdict styling token-based", () => {
    document.documentElement.dataset.theme = "light";
    render(<VerdictBadge verdict="unreliable" />);
    expect(screen.getByText("unreliable")).toHaveClass("border-verdict-unreliable/55", "text-verdict-unreliable");
  });
});
