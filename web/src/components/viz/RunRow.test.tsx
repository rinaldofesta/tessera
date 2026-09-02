import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { runFixture } from "@/test/fixtures";
import { RunRow } from "./RunRow";

afterEach(cleanup);

describe("RunRow", () => {
  it("has no checkbox and exposes the report actions", () => {
    render(<MemoryRouter><RunRow run={runFixture()} onSave={vi.fn()} onArchive={vi.fn()} /></MemoryRouter>);
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open" })).toHaveAttribute("href", "/reports/run-1");
    expect(screen.getByRole("link", { name: "Run again" })).toHaveAttribute("href", expect.stringContaining("model=anthropic%2Fclaude-sonnet-4"));
    expect(screen.getByRole("button", { name: "Save HTML" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Archive" })).toBeInTheDocument();
  });

  it("hides Archive for bundled reports", () => {
    render(<MemoryRouter><RunRow run={runFixture({ source: "bundled" })} /></MemoryRouter>);
    expect(screen.queryByRole("button", { name: "Archive" })).not.toBeInTheDocument();
  });
});
