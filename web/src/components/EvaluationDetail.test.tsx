import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { EvaluationSummary } from "@/types";
import { EvaluationDetail } from "./EvaluationDetail";

afterEach(cleanup);

const item = {
  id: "run:a", kind: "run", source: "api", status: "done",
  created_at: "2026-08-29T14:02:11Z", model: "anthropic/claude-sonnet-4",
  org: "meridian", engine: "llm", grader: null, epochs: 3,
  pass_k_rate: 0.72, mean_rate: 0.94, artifact_path: null, artifact_sha256: null,
  protocol_hash: "abcdef0123456789deadbeef", execution_hash: "fedcba9876543210cafebabe",
  receipt: {
    protocol_hash: "abcdef0123456789deadbeef",
    execution_hash: "fedcba9876543210cafebabe",
    protocol: {}, artifact: {},
    runtime: { effective_models: ["claude-sonnet-4"] },
    timing: { duration_seconds: 42.5 },
    usage: { billed_cost: 0.1234 },
  },
} as unknown as EvaluationSummary;

describe("EvaluationDetail", () => {
  it("shows fingerprints, effective model, and cost", () => {
    render(
      <EvaluationDetail
        item={item}
        diagnostics={{ loading: false, error: null, data: [{ kind: "tool_error", signature: "timeout", count: 3 }] }}
      />,
    );
    expect(screen.getByText(/abcdef0123456789/)).toBeInTheDocument();
    expect(screen.getByText("claude-sonnet-4")).toBeInTheDocument();
    expect(screen.getByText(/tool error · timeout/)).toBeInTheDocument();
    expect(screen.getByText("×3")).toBeInTheDocument();
  });

  it("says so when there are no signatures", () => {
    render(<EvaluationDetail item={item} diagnostics={{ loading: false, error: null, data: [] }} />);
    expect(screen.getByText("no recorded failure signatures")).toBeInTheDocument();
  });
});
