import { describe, expect, it } from "vitest";
import type { ComparisonResult } from "@/types";
import { driftSummary, parseEvalsParam, planPairs } from "./comparePlan";

const result = (over: Partial<ComparisonResult>): ComparisonResult => ({
  compatible: true,
  intervention: "model",
  changed_dimensions: ["model"],
  unexpected_dimensions: [],
  overall: {
    matched: 10, a_wins: 1, b_wins: 3,
    both_pass: 5, both_fail: 1, discordant: 4, p_value: 0.05, dropped: [],
  },
  categories: [],
  diagnostics: { a: [], b: [] },
  ...over,
});

describe("parseEvalsParam", () => {
  it("splits, trims, dedupes, preserves order", () => {
    expect(parseEvalsParam("run:a, run:b,run:a,,run:c")).toEqual(["run:a", "run:b", "run:c"]);
  });
  it("returns empty for null", () => {
    expect(parseEvalsParam(null)).toEqual([]);
  });
});

describe("planPairs", () => {
  it("pairs the first selection against every other", () => {
    expect(planPairs(["a", "b", "c"])).toEqual([
      { baseline: "a", challenger: "b" },
      { baseline: "a", challenger: "c" },
    ]);
  });
  it("needs at least two", () => {
    expect(planPairs(["a"])).toEqual([]);
    expect(planPairs([])).toEqual([]);
  });
});

describe("driftSummary", () => {
  it("is compatible only when every pair is", () => {
    const ok = driftSummary([
      { challenger: "b", result: result({}) },
      { challenger: "c", result: result({ changed_dimensions: ["model", "seed"] }) },
    ]);
    expect(ok.compatible).toBe(true);
    expect(ok.changed).toEqual(["model", "seed"]);
    expect(ok.unexpectedByChallenger).toEqual([]);
  });
  it("attributes unexpected dimensions per challenger", () => {
    const bad = driftSummary([
      { challenger: "b", result: result({}) },
      { challenger: "c", result: result({ compatible: false, unexpected_dimensions: ["seed", "k"] }) },
    ]);
    expect(bad.compatible).toBe(false);
    expect(bad.unexpectedByChallenger).toEqual([{ challenger: "c", dims: ["seed", "k"] }]);
  });
});
