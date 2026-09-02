import { pct } from "./format";
import type { Run } from "@/types";

export function summaryText(run: Run): string {
  if (!run.verdict) throw new Error("This run has no verdict to summarize.");
  return [
    run.verdict.sentence,
    `pass^${run.request.k} ${pct(run.verdict.pass_k_rate)} · mean ${pct(run.verdict.mean_rate)} · ${run.request.suite} · ${run.request.model} · ${run.request.k} repeats`,
    `tessera report ${run.id}`,
  ].join("\n");
}
