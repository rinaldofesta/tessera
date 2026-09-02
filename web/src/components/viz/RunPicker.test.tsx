import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { EvaluationSummary } from "@/types";
import { COMPARE_PALETTE } from "@/copy";
import { RunPicker } from "./RunPicker";

afterEach(cleanup);

const ev = (over: Partial<EvaluationSummary>): EvaluationSummary =>
  ({
    id: "run:a", kind: "run", source: "api", status: "done",
    created_at: "2026-08-29T14:02:11Z", model: "anthropic/claude-sonnet-4",
    org: "meridian", engine: "llm", grader: null, epochs: 3,
    pass_k_rate: 0.72, mean_rate: 0.94, artifact_path: null, artifact_sha256: null,
    protocol_hash: "p", execution_hash: "x",
    receipt: {} as EvaluationSummary["receipt"],
    ...over,
  }) as EvaluationSummary;

const evals = [ev({ id: "run:a" }), ev({ id: "run:b", model: "openai/gpt-5.2" })];

describe("RunPicker", () => {
  it("lists evaluations with identity and score", () => {
    render(<RunPicker evaluations={evals} selected={[]} onToggle={vi.fn()} onInspect={vi.fn()} />);
    expect(screen.getByText("claude-sonnet-4")).toBeInTheDocument();
    expect(screen.getByText("gpt-5.2")).toBeInTheDocument();
    expect(screen.getAllByText("72%").length).toBeGreaterThan(0);
  });

  it("appends to the ordered selection on select", async () => {
    const onToggle = vi.fn();
    render(<RunPicker evaluations={evals} selected={["run:b"]} onToggle={onToggle} onInspect={vi.fn()} />);
    await userEvent.click(screen.getByRole("checkbox", { name: /claude-sonnet-4/ }));
    expect(onToggle).toHaveBeenCalledWith(["run:b", "run:a"]);
  });

  it("removes from the selection on deselect", async () => {
    const onToggle = vi.fn();
    render(<RunPicker evaluations={evals} selected={["run:b", "run:a"]} onToggle={onToggle} onInspect={vi.fn()} />);
    await userEvent.click(screen.getByRole("checkbox", { name: /gpt-5.2/ }));
    expect(onToggle).toHaveBeenCalledWith(["run:a"]);
  });

  it("marks the first selection as the baseline and colors by order", () => {
    render(<RunPicker evaluations={evals} selected={["run:b", "run:a"]} onToggle={vi.fn()} onInspect={vi.fn()} />);
    expect(screen.getByText("baseline")).toBeInTheDocument();
    const dots = screen.getAllByTestId("color-dot");
    expect(dots[0].style.background).toBeTruthy();
  });

  it("caps the selection at 8", () => {
    const many = Array.from({ length: 9 }, (_, i) => ev({ id: `run:${i}`, model: `m/${i}` }));
    render(
      <RunPicker
        evaluations={many}
        selected={many.slice(0, 8).map((e) => e.id)}
        onToggle={vi.fn()}
        onInspect={vi.fn()}
      />,
    );
    expect(screen.getByRole("checkbox", { name: /^8 · / })).toBeDisabled();
  });

  it("fires onInspect from the row affordance", async () => {
    const onInspect = vi.fn();
    render(<RunPicker evaluations={evals} selected={[]} onToggle={vi.fn()} onInspect={onInspect} />);
    await userEvent.click(screen.getAllByRole("button", { name: "receipt & diagnostics" })[0]);
    expect(onInspect).toHaveBeenCalledWith("run:a");
  });
});

void COMPARE_PALETTE;
