import type { ComparisonResult } from "@/types";

/** ?evals=run:a,run:b → ordered unique ids. Order is meaning: first = baseline. */
export function parseEvalsParam(param: string | null): string[] {
  if (!param) return [];
  return [...new Set(param.split(",").map((s) => s.trim()).filter(Boolean))];
}

/** The API is strictly pairwise; N selections become N−1 baseline-vs-challenger calls. */
export function planPairs(selected: string[]): { baseline: string; challenger: string }[] {
  if (selected.length < 2) return [];
  const [baseline, ...rest] = selected;
  return rest.map((challenger) => ({ baseline, challenger }));
}

export interface PairOutcome {
  challenger: string;
  result: ComparisonResult;
}

/** Banner input: green only when every pair is compatible; drift is attributed per challenger. */
export function driftSummary(pairs: PairOutcome[]): {
  compatible: boolean;
  changed: string[];
  unexpectedByChallenger: { challenger: string; dims: string[] }[];
} {
  return {
    compatible: pairs.every((p) => p.result.compatible),
    changed: [...new Set(pairs.flatMap((p) => p.result.changed_dimensions))],
    unexpectedByChallenger: pairs
      .filter((p) => p.result.unexpected_dimensions.length > 0)
      .map((p) => ({ challenger: p.challenger, dims: p.result.unexpected_dimensions })),
  };
}
