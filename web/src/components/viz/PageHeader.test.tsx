import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { PageHeader } from "./PageHeader";
import { SectionLabel } from "./SectionLabel";

afterEach(cleanup);

describe("PageHeader", () => {
  it("renders eyebrow, title, and subtitle", () => {
    render(<PageHeader eyebrow="Run history" title="Every evaluation" subtitle="raw runs" />);
    expect(screen.getByText("Run history")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Every evaluation" })).toBeInTheDocument();
    expect(screen.getByText("raw runs")).toBeInTheDocument();
  });

  it("omits the subtitle node when not given", () => {
    render(<PageHeader eyebrow="E" title="T" />);
    expect(screen.queryByText("raw runs")).not.toBeInTheDocument();
  });

  it("renders actions when given", () => {
    render(<PageHeader eyebrow="E" title="T" actions={<button>act</button>} />);
    expect(screen.getByRole("button", { name: "act" })).toBeInTheDocument();
  });
});

describe("SectionLabel", () => {
  it("renders its children", () => {
    render(<SectionLabel>failures</SectionLabel>);
    expect(screen.getByText("failures")).toBeInTheDocument();
  });
});
