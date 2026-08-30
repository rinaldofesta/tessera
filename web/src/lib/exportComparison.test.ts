import { describe, expect, it, vi } from "vitest";
import type { ComparisonResult, EvaluationSummary } from "@/types";
import { exportComparisonHtml, exportComparisonJson } from "./exportComparison";

const XSS = "<script>alert(1)</script>";

const evaluation = {
  id: "run:a", kind: "run", source: "api", status: "done",
  created_at: "2026-08-29T14:02:11Z", model: `anthropic/${XSS}`,
  org: "meridian", engine: "llm", grader: null, epochs: 3,
  pass_k_rate: 0.72, mean_rate: 0.94, artifact_path: null, artifact_sha256: null,
  protocol_hash: "p", execution_hash: "x", receipt: {},
} as unknown as EvaluationSummary;

const result: ComparisonResult = {
  compatible: false,
  intervention: "model",
  changed_dimensions: ["model"],
  unexpected_dimensions: [`seed ${XSS}`],
  overall: {
    matched: 12, a_wins: 2, b_wins: 5,
    both_pass: 4, both_fail: 1, discordant: 7, p_value: 0.0312, dropped: [],
  },
  categories: [
    {
      key: "unresolvable", matched: 6, a_wins: 1, b_wins: 3,
      both_pass: 1, both_fail: 1, discordant: 4, p_value: 0.05, dropped: [],
    },
  ],
  diagnostics: { a: [], b: [] },
};

const data = {
  generated_at: "2026-08-30T12:00:00Z",
  intervention: "model",
  evaluations: [evaluation],
  pairs: [{ challenger: "run:b", result }],
};

describe("exportComparisonHtml", () => {
  const html = exportComparisonHtml(data);
  it("contains no script tags and escapes hostile strings", () => {
    expect(html.toLowerCase()).not.toContain("<script");
    expect(html).toContain("&lt;script&gt;");
  });
  it("is a standalone document with the drift verdict and pair table", () => {
    expect(html).toContain("<!doctype html>");
    expect(html).toContain("Protocol drift detected");
    expect(html).toContain("0.0312");
  });
});

describe("exportComparisonJson", () => {
  it("round-trips", () => {
    expect(JSON.parse(exportComparisonJson(data))).toEqual(data);
  });
});

void vi;
