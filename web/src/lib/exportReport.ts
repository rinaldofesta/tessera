import { tilesFrom } from "@/components/VerdictMosaic";
import { gapPoints } from "@/components/viz/GapBar";
import { whyFailed } from "@/components/viz/VerdictBadge";
import { GAP_COPY, REPORT_COPY, conflictLabel } from "@/copy";
import type { Report, Run } from "@/types";
import { downloadText } from "./download";
import { escapeHtml } from "./escapeHtml";
import { fmtTs, pct, shortModel } from "./format";

export { escapeHtml as esc } from "./escapeHtml";
const e = (value: unknown) => escapeHtml(String(value ?? "—"));

export function filenameSegment(value: string): string {
  return value.replace(/[^A-Za-z0-9._-]+/g, "-").replace(/\.{2,}/g, "-").replace(/^-+|-+$/g, "");
}

export function reportFilename(report: Report, ext: "html" | "json"): string {
  const date = filenameSegment(report.header.created.slice(0, 10)) || "undated";
  return `tessera-${filenameSegment(report.header.org ?? "run")}-${filenameSegment(shortModel(report.header.model))}-${date}.${ext}`;
}

export const exportReportJson = (report: Report): string => JSON.stringify(report, null, 2);

export function downloadReport(run: Run, format: "html" | "json" = "html"): void {
  if (!run.report) throw new Error("This run has no report to export.");
  const text = format === "html" ? exportReportHtml(run) : exportReportJson(run.report);
  downloadText(reportFilename(run.report, format), text, format === "html" ? "text/html" : "application/json");
}

const CSS = `
  :root{color-scheme:dark}*{box-sizing:border-box}body{margin:0 auto;max-width:900px;padding:40px 24px;background:#14161a;color:#e8eaf0;font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}h1{font-size:30px;margin:4px 0}h2{font-size:12px;text-transform:uppercase;letter-spacing:.14em;color:#9aa1b0;margin:28px 0 10px}.muted{color:#9aa1b0}.faint{color:#6b7280;font-size:12px}.card{background:#1c1f26;border:1px solid #2e3340;border-radius:12px;padding:14px 16px;margin:8px 0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.stat b{display:block;font-size:24px}.mosaic{display:grid;gap:3px;margin:18px 0}.mosaic i{aspect-ratio:1;border:1px solid;border-radius:3px}.mosaic .pass{background:#21482d;border-color:#4ade80}.mosaic .fail{background:#522b2e;border-color:#f87171}.bar{height:10px;background:#232732;border-radius:999px;overflow:hidden;display:flex}.bar div:first-child{background:#8b93ff}.bar .gap{background:repeating-linear-gradient(45deg,#8b6419 0 3px,transparent 3px 6px)}.legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:6px;font-size:12px;color:#9aa1b0}.legend i{display:inline-block;width:9px;height:9px;margin-right:5px;border-radius:50%}.legend .every{background:#8b93ff}.legend .sometimes{background:#fbbf24}.legend .never{background:#232732;border:1px solid #2e3340}table{border-collapse:collapse;width:100%}td,th{padding:6px 8px;text-align:left;border-bottom:1px solid #2e3340;vertical-align:top}blockquote{margin:4px 0;padding-left:10px;border-left:2px solid #f87171;color:#9aa1b0}.receipt{word-break:break-word}@media print{:root{color-scheme:light}body{background:#fff;color:#15171b;padding:20px}.card{background:#fff;border-color:#c9cdd6}.muted,.faint,h2{color:#4b5563}.bar{background:#e5e7eb}.mosaic .pass{background:#c9f5d5}.mosaic .fail{background:#fbd2d2}details>*{display:block!important}}
`;

function bar(passK: number, mean: number): string {
  const p = Math.min(1, Math.max(0, passK));
  const m = Math.max(p, Math.min(1, Math.max(0, mean)));
  return `<div class="bar"><div style="width:${e((p * 100).toFixed(2))}%"></div><div class="gap" style="width:${e(((m - p) * 100).toFixed(2))}%"></div></div>`;
}

// Falls back to report.header/run.request the same way the on-screen Details receipt
// table does, so the exported HTML never shows "—" where Details shows a real value.
const receiptRows = (run: Run): [string, unknown][] => run.receipt ? [
  ["scorer version", run.receipt.protocol.scorer_version ?? run.report?.header.scorer_version ?? null],
  ["scaffold", run.receipt.protocol.scaffold ?? run.request.scaffold],
  ["seed", run.receipt.protocol.seed ?? run.request.seed], ["repeats", run.receipt.protocol.epochs], ["protocol hash", run.receipt.protocol_hash], ["execution hash", run.receipt.execution_hash],
  ["artifact path", run.receipt.artifact.path], ["artifact sha256", run.receipt.artifact.sha256], ["blueprint sha256", run.receipt.protocol.blueprint_sha256],
  ["engine", run.receipt.protocol.engine], ["grader", run.receipt.protocol.grader], ["harness", run.receipt.protocol.harness],
  ["suite org", run.receipt.protocol.org], ["requested model", run.receipt.runtime.requested_model], ["reported model", run.receipt.runtime.reported_model],
  ["effective models", run.receipt.runtime.effective_models.join(", ")], ["Tessera version", run.receipt.runtime.tessera_version],
  ["Inspect version", run.receipt.runtime.inspect_ai_version], ["git revision", run.receipt.runtime.git_revision], ["git dirty", run.receipt.runtime.git_dirty],
  ["started", run.receipt.timing.started_at], ["completed", run.receipt.timing.completed_at], ["duration seconds", run.receipt.timing.duration_seconds],
  ["input tokens", run.receipt.usage.input_tokens], ["output tokens", run.receipt.usage.output_tokens], ["total tokens", run.receipt.usage.total_tokens],
  ["billed cost", run.receipt.usage.billed_cost], ["log path", run.paths.log],
] : [["log path", run.paths.log]];

/** Standalone, script-free report. All run-derived values pass through `escapeHtml`. */
export function exportReportHtml(run: Run): string {
  const report = run.report;
  const verdict = run.verdict;
  if (!report || !verdict) throw new Error("This run has no completed report.");
  const gap = gapPoints(verdict.pass_k_rate, verdict.mean_rate);
  const tiles = tilesFrom(report).map((tile) => tile === "pass" ? '<i class="pass"></i>' : '<i class="fail"></i>').join("");
  const categories = report.categories.map((category) => `<tr><td>${e(conflictLabel(category.key))}</td><td>${e(pct(category.pass_k_rate))}</td><td>${e(pct(category.mean_rate))}</td></tr>`).join("");
  const axes = [[REPORT_COPY.axisAccuracy, report.axes.accuracy_rate], [REPORT_COPY.axisProvenance, report.axes.provenance_rate], [REPORT_COPY.axisRefusal, report.axes.refusal_rate]]
    .map(([label, value]) => `<div class="card stat"><span class="faint">${e(label)}</span><b>${e(pct(value as number | null))}</b></div>`).join("");
  const failures = report.probes.flatMap((probe) => probe.failures.map((failure) => `<div class="card"><b>${e(probe.probe_id)} · ${e(conflictLabel(probe.conflict_type))} · ${e(whyFailed(probe.expected_behavior, failure))}</b><p>${e(failure.question)}</p><blockquote>${e(failure.answer)}</blockquote><p class="faint">${e(`repeat ${failure.epoch} · consulted: ${failure.consulted.join(", ") || "(none)"} · expected: ${failure.expected_sources.join(", ") || "(none)"} · missing: ${failure.missing.join(", ") || "(none)"}`)}</p></div>`)).join("") || `<p class="muted">${e(REPORT_COPY.noFailures(report.probes.length))}</p>`;
  const diagnostics = run.diagnostics.map((item) => `<li>${e(item.kind)} · ${e(item.signature)} · ${e(item.count)}</li>`).join("") || `<li>${e("none")}</li>`;
  const receipt = receiptRows(run).map(([label, value]) => `<tr><th>${e(label)}</th><td>${e(value)}</td></tr>`).join("");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tessera — ${e(run.request.model)} on ${e(run.request.suite)}</title><style>${CSS}</style></head><body>
<p class="faint">${e(run.request.suite)} · ${e(run.request.model)} · ${e(run.request.k)} repeats · ${e(fmtTs(run.created_at))} · ${e(run.id)}</p><h1>${e(verdict.sentence)}</h1>
<div class="mosaic" style="grid-template-columns:repeat(${e(Math.max(1, report.probes.length))},minmax(0,44px))">${tiles}</div><p class="faint">${e(`${report.probes.length} questions × ${run.request.k} repeats · one square per answer`)}</p>
${bar(verdict.pass_k_rate, verdict.mean_rate)}<div class="legend"><span><i class="every"></i>${e(GAP_COPY.rightEveryTime)} ${e(pct(verdict.pass_k_rate))}</span><span><i class="sometimes"></i>${e(GAP_COPY.onlySometimes)} +${e(gap)} pp</span><span><i class="never"></i>${e(GAP_COPY.never)}</span></div>
<div class="grid"><div class="card stat"><span class="faint">${e(`pass^${run.request.k} — ${GAP_COPY.rightEveryTime}`)}</span><b>${e(pct(verdict.pass_k_rate))}</b></div><div class="card stat"><span class="faint">${e("mean — right on average")}</span><b>${e(pct(verdict.mean_rate))}</b></div></div>
<h2>${e(REPORT_COPY.categories)}</h2><table><thead><tr><th>${e("category")}</th><th>${e(`pass^${run.request.k}`)}</th><th>${e("mean")}</th></tr></thead><tbody>${categories}</tbody></table>
<h2>${e(REPORT_COPY.axes)}</h2><div class="grid">${axes}</div><h2>${e(REPORT_COPY.failures)}</h2>${failures}
<h2>${e(REPORT_COPY.diagnostics)}</h2><ul>${diagnostics}</ul><h2>${e(REPORT_COPY.receipt)}</h2><table class="receipt">${receipt}</table></body></html>`;
}
