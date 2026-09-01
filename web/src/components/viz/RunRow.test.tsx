import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RunSummary } from "@/types";
import { RunRow } from "./RunRow";

afterEach(cleanup);

const doneRun: RunSummary = {
  id: "abc123",
  status: "done",
  error: null,
  model: "anthropic/claude-sonnet-4",
  org: "meridian",
  judge: "llm",
  grader: "openai/gpt-5.2",
  epochs: 5,
  created_at: "2026-08-29T14:02:11Z",
  finished_at: "2026-08-29T14:31:40Z",
  pass_k_rate: 0.72,
  mean_rate: 0.94,
  archived: false,
};

const runningRun: RunSummary = {
  ...doneRun,
  id: "def456",
  status: "running",
  finished_at: null,
  pass_k_rate: null,
  mean_rate: null,
};

const erroredRun: RunSummary = {
  ...doneRun,
  id: "ghi789",
  status: "error",
  error: "provider timeout after probe 7",
  pass_k_rate: null,
  mean_rate: null,
};

const renderRow = (run: RunSummary, onSelect = vi.fn()) => {
  render(
    <MemoryRouter>
      <RunRow run={run} selected={false} onSelect={onSelect} />
    </MemoryRouter>,
  );
  return onSelect;
};

describe("RunRow", () => {
  it("shows the gap bar and headline for a finished run", () => {
    renderRow(doneRun);
    expect(screen.getByRole("img")).toHaveAttribute(
      "aria-label",
      "72% reliable (pass^5), 94% mean success, 22 point gap",
    );
    expect(screen.getByText("72%")).toBeInTheDocument();
    expect(screen.getByText("pass^5 · mean 94% · gap 22 pp")).toBeInTheDocument();
  });

  it("identifies the run: short model name + suite · grading · repeats", () => {
    renderRow(doneRun);
    expect(screen.getByText("claude-sonnet-4")).toBeInTheDocument();
    expect(screen.getByText("meridian · ai grader · 5 repeats")).toBeInTheDocument();
  });

  it("shows a lifecycle badge instead of a gap bar while running", () => {
    renderRow(runningRun);
    expect(screen.getByText("running…")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("shows the error text on a failed run", () => {
    renderRow(erroredRun);
    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(screen.getByText("provider timeout after probe 7")).toBeInTheDocument();
  });

  it("only finished runs are selectable", () => {
    renderRow(doneRun);
    expect(screen.getByRole("checkbox")).toBeEnabled();
  });

  it("disables selection for running and errored runs", () => {
    renderRow(runningRun);
    expect(screen.getByRole("checkbox")).toBeDisabled();
  });

  it("reports selection changes with the run id", async () => {
    const onSelect = renderRow(doneRun);
    await userEvent.click(screen.getByRole("checkbox"));
    expect(onSelect).toHaveBeenCalledWith("abc123", true);
  });

  it("links Details to the run and Rerun to a prefilled launcher", () => {
    renderRow(doneRun);
    expect(screen.getByRole("link", { name: "Details" })).toHaveAttribute("href", "/runs/abc123");
    expect(screen.getByRole("link", { name: "Rerun" })).toHaveAttribute("href", "/new?from=abc123");
  });
});
