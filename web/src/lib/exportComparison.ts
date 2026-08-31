import { gapPoints } from "@/components/viz/GapBar";
import { COMPARE_COPY, conflictLabel } from "@/copy";
import { pct, pValue, shortModel } from "@/lib/format";
import type { EvaluationSummary } from "@/types";
import { downloadText } from "@/lib/download";
import { esc, filenameSegment } from "./exportReport";
import { driftSummary, type PairOutcome } from "./comparePlan";

export interface ComparisonExport {
  generated_at: string;
  intervention: string;
  evaluations: EvaluationSummary[];
  pairs: PairOutcome[];
}

export function exportComparisonJson(data: ComparisonExport): string {
  return JSON.stringify(data, null, 2);
}

const CSS = `
  :root { color-scheme: dark; }
  body { margin: 0 auto; max-width: 860px; padding: 40px 24px; background: #14161a; color: #e8eaf0;
    font: 14px/1.6 -apple-system, "Segoe UI", sans-serif; }
  h1 { font-size: 22px; letter-spacing: -0.02em; margin: 0 0 12px; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.16em; color: #9aa1b0; margin: 28px 0 10px; }
  .card { background: #1c1f26; border: 1px solid #2e3340; border-radius: 12px; padding: 12px 16px; margin: 8px 0; }
  .ok { border-color: #4ade80; } .bad { border-color: #f87171; }
  .faint { color: #6b7280; font-size: 12px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th { text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: .12em; color: #6b7280;
    border-bottom: 1px solid #2e3340; padding: 4px 8px 4px 0; }
  td { padding: 4px 8px 4px 0; border-bottom: 1px solid #232732; }
  td.n { text-align: right; font-variant-numeric: tabular-nums; }
`;

export function exportComparisonHtml(data: ComparisonExport): string {
  // Mirror AdHocTab's live banner exactly (same driftSummary, same copy) instead of
  // re-deriving drift ad hoc — the export previously dropped the "changed dimensions"
  // disclosure the live UI shows on a controlled (non-drifting) comparison.
  const summary = driftSummary(data.pairs);
  const banner = summary.compatible
    ? `<div class="card ok"><b>${esc(COMPARE_COPY.controlled)}</b> — ${esc(
        COMPARE_COPY.controlledDetail(data.intervention, summary.changed.join(", ")),
      )}</div>`
    : `<div class="card bad"><b>${esc(COMPARE_COPY.drift)}</b> — ${summary.unexpectedByChallenger
        .map(({ challenger, dims }) => esc(COMPARE_COPY.driftDetail(challenger, dims.join(", "))))
        .join("; ")}</div>`;

  const evals = data.evaluations
    .map(
      (e) => `<div class="card"><b>${esc(shortModel(e.model))}</b>
      <span class="faint">${esc(e.org ?? "")} · ${e.epochs}×</span>
      — ${pct(e.pass_k_rate)} pass^${e.epochs} · mean ${pct(e.mean_rate)} · gap ${gapPoints(
        e.pass_k_rate ?? 0,
        e.mean_rate ?? 0,
      )} pp</div>`,
    )
    .join("");

  const headerRow = `<tr>${[
    COMPARE_COPY.significanceCols.category,
    COMPARE_COPY.significanceCols.matched,
    COMPARE_COPY.significanceCols.aWins,
    COMPARE_COPY.significanceCols.bWins,
    COMPARE_COPY.significanceCols.p,
  ].map((col) => `<th>${esc(col)}</th>`).join("")}</tr>`;

  const pairTables = data.pairs
    .map((p) => {
      const rows = [...p.result.categories, { ...p.result.overall, key: "OVERALL" }]
        .map(
          (row) => `<tr><td>${esc(row.key === "OVERALL" ? "OVERALL" : conflictLabel(row.key))}</td>
          <td class="n">${row.matched}</td><td class="n">${row.a_wins}</td>
          <td class="n">${row.b_wins}</td><td class="n">${pValue(row.p_value)}</td></tr>`,
        )
        .join("");
      const dropped = p.result.overall.dropped;
      const unmatched = dropped.length > 0
        ? `<p class="faint">${esc(COMPARE_COPY.unmatched(dropped.length, dropped.join(", ")))}</p>`
        : "";
      return `<h2>${esc(COMPARE_COPY.pairHeading(p.challenger))}</h2>
      <table>${headerRow}${rows}</table>${unmatched}`;
    })
    .join("");

  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(COMPARE_COPY.exportTitle(data.evaluations.length))}</title><style>${CSS}</style></head><body>
<h1>${esc(COMPARE_COPY.exportHeading)}</h1>
<p class="faint">${esc(data.generated_at)} · ${esc(COMPARE_COPY.intervention)}: ${esc(data.intervention)}</p>
${banner}
<h2>${esc(COMPARE_COPY.gapPanel)}</h2>${evals}
${pairTables}
</body></html>`;
}

export function downloadComparison(data: ComparisonExport, format: "html" | "json"): void {
  const date = filenameSegment(data.generated_at.slice(0, 10)) || "undated";
  const name = `tessera-comparison-${data.evaluations.length}-evals-${date}.${format}`;
  const text = format === "html" ? exportComparisonHtml(data) : exportComparisonJson(data);
  downloadText(name, text, format === "html" ? "text/html" : "application/json");
}
