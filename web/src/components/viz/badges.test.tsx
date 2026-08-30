import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";
import { VerdictBadge, verdictOf } from "./VerdictBadge";

describe("StatusBadge", () => {
  it("names each lifecycle state", () => {
    const { rerender } = render(<StatusBadge status="running" />);
    expect(screen.getByText("running…")).toBeInTheDocument();
    rerender(<StatusBadge status="done" />);
    expect(screen.getByText("finished")).toBeInTheDocument();
    rerender(<StatusBadge status="error" />);
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("keeps 'done' neutral — no verdict color classes", () => {
    render(<StatusBadge status="done" />);
    const el = screen.getByText("finished");
    expect(el.className).not.toMatch(/verdict-reliable/);
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
