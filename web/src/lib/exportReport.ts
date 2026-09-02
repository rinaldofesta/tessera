import { SCORECARD_COPY, VERDICT_COPY, conflictLabel } from "@/copy";
import { downloadText } from "./download";
import { gapPoints } from "@/components/viz/GapBar";
import { whyFailed } from "@/components/viz/VerdictBadge";
import { fmtTs, pct, shortModel } from "@/lib/format";
import type { Report } from "@/types";

/** Escape the five HTML metacharacters. Every report string passes through here. */
export function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Restrict a user-derived filename segment to safe, portable characters. */
export function filenameSegment(s: string): string {
  return s
    .replace(/[^A-Za-z0-9._-]+/g, "-")
    .replace(/\.{2,}/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function reportFilename(report: Report, ext: "html" | "json"): string {
  const date = filenameSegment(report.header.created.slice(0, 10)) || "undated";
  return `tessera-${filenameSegment(report.header.org ?? "run")}-${filenameSegment(shortModel(report.header.model))}-${date}.${ext}`;
}

export function exportReportJson(report: Report): string {
  return JSON.stringify(report, null, 2);
}

export function downloadReport(report: Report, format: "html" | "json"): void {
  const text = format === "html" ? exportReportHtml(report) : exportReportJson(report);
  downloadText(
    reportFilename(report, format),
    text,
    format === "html" ? "text/html" : "application/json",
  );
}

const CSS = `
  :root { color-scheme: dark; }
  body { margin: 0 auto; max-width: 860px; padding: 40px 24px; background: #14161a; color: #e8eaf0;
    font: 14px/1.6 -apple-system, "Segoe UI", sans-serif; }
  h1 { font-size: 24px; letter-spacing: -0.02em; margin: 0 0 4px; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.16em; color: #9aa1b0; margin: 28px 0 10px; }
  .muted { color: #9aa1b0; } .faint { color: #6b7280; font-size: 12px; }
  .card { background: #1c1f26; border: 1px solid #2e3340; border-radius: 12px; padding: 14px 16px; margin: 8px 0; }
  .verdict-bad { border-color: #f87171; } .verdict-ok { border-color: #4ade80; }
  .tiles { display: flex; gap: 10px; flex-wrap: wrap; } .tiles .card { flex: 1; min-width: 140px; margin: 0; }
  .tiles b { font-size: 22px; display: block; }
  .bar { height: 10px; background: #232732; border-radius: 5px; overflow: hidden; display: flex; margin: 4px 0 2px; }
  .bar i { display: block; height: 100%; background: #8b93ff; } .bar i.full { background: #4ade80; }
  .bar em { display: block; height: 100%;
    background: repeating-linear-gradient(45deg, rgba(251,191,36,.6) 0 3px, transparent 3px 6px); }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  td { padding: 4px 8px 4px 0; vertical-align: top; }
  details { margin: 8px 0; } summary { cursor: pointer; font-weight: 600; }
  blockquote { margin: 4px 0; padding-left: 10px; border-left: 2px solid #2e3340; color: #9aa1b0; font-style: italic; }
`;

function bar(passK: number, mean: number): string {
  const clamp01 = (x: number) => (Number.isFinite(x) ? Math.min(1, Math.max(0, x)) : 0);
  const p = clamp01(passK);
  const m = Math.max(clamp01(mean), p);
  const fill = `<i${p >= 1 - 1e-9 ? ' class="full"' : ""} style="width:${(p * 100).toFixed(2)}%"></i>`;
  const gap = `<em style="width:${((m - p) * 100).toFixed(2)}%"></em>`;
  return `<div class="bar">${fill}${gap}</div>`;
}

/** Self-contained, script-free scorecard document. Native <details> for failures. */
export function exportReportHtml(report: Report): string {
  const h = report.header;
  const failed = report.probes.filter((p) => !p.pass_k);
  const failedCats = report.categories.filter((c) => c.pass_k_rate < 1);
  const gapPp = gapPoints(report.overall.pass_k_rate, report.overall.mean_rate);

  const verdict = failedCats.length === 0
    ? `<div class="card verdict-ok"><b>✓</b> ${esc(SCORECARD_COPY.reliableVerdict(h.k))}</div>`
    : `<div class="card verdict-bad"><b>✗</b> ${esc(
        SCORECARD_COPY.notReliableVerdict(failedCats.map((c) => conflictLabel(c.key)).join(", ")),
      )}</div>`;

  const categories = report.categories
    .map(
      (c) => `<div class="card">
        <table><tr><td>${esc(conflictLabel(c.key))}</td>
        <td style="text-align:right"><b>${pct(c.pass_k_rate)}</b> <span class="faint">${esc(SCORECARD_COPY.categoryLine(h.k, pct(c.mean_rate)))}</span></td></tr></table>
        ${bar(c.pass_k_rate, c.mean_rate)}</div>`,
    )
    .join("");

  const axes = `<div class="tiles">
    <div class="card"><span class="faint">${esc(SCORECARD_COPY.axisAccuracy)}</span><b>${pct(report.axes.accuracy_rate)}</b><span class="faint">${esc(SCORECARD_COPY.axisAccuracySub(report.axes.n_answer_epochs))}</span></div>
    <div class="card"><span class="faint">${esc(SCORECARD_COPY.axisProvenance)}</span><b>${pct(report.axes.provenance_rate)}</b><span class="faint">${esc(SCORECARD_COPY.axisProvenanceSub(report.axes.n_total_epochs))}</span></div>
    <div class="card"><span class="faint">${esc(SCORECARD_COPY.axisRefusal)}</span><b>${pct(report.axes.refusal_rate)}</b><span class="faint">${esc(SCORECARD_COPY.axisRefusalSub(report.axes.n_refuse_epochs))}</span></div>
    ${report.axes.answer_format_rate != null ? `<div class="card"><span class="faint">${esc(SCORECARD_COPY.axisFormat)}</span><b>${pct(report.axes.answer_format_rate)}</b><span class="faint">${esc(SCORECARD_COPY.axisFormatSub)}</span></div>` : ""}
  </div>`;

  const failures = failed.length === 0
    ? `<p class="muted">${esc(SCORECARD_COPY.noFailures(report.probes.length))}</p>`
    : failed
        .map(
          (p) => `<details class="card"><summary>${esc(VERDICT_COPY[p.epochs_passed > 0 ? "inconsistent" : "unreliable"])} · ✗ ${esc(p.probe_id)} · ${esc(
            conflictLabel(p.conflict_type),
          )} <span class="faint">${esc(SCORECARD_COPY.probesPassed(p.epochs_passed, p.epochs_total))}</span></summary>
          ${p.failures[0] ? `<p><span class="muted">${esc(SCORECARD_COPY.question)}</span> ${esc(p.failures[0].question)}</p>` : ""}
          <p><span class="muted">${esc(SCORECARD_COPY.expected)}</span> ${esc(p.expected_behavior === "refuse" ? SCORECARD_COPY.expectRefuse : SCORECARD_COPY.expectAnswer)}</p>
          ${p.failures
            .map(
              (f) => `<p><b>${esc(SCORECARD_COPY.repeatFailed(f.epoch, whyFailed(p.expected_behavior, f)))}</b></p>
              <blockquote>"${esc(f.answer)}"</blockquote>
              <p class="faint">${esc(SCORECARD_COPY.consulted(f.consulted.join(", ") || SCORECARD_COPY.none))}${
                f.missing.length > 0 ? ` · ${esc(SCORECARD_COPY.missing)} <b>${esc(f.missing.join(", "))}</b>` : ""
              }</p>`,
            )
            .join("")}</details>`,
        )
        .join("");

  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>tessera — ${esc(shortModel(h.model))} on ${esc(h.org ?? "run")}</title><style>${CSS}</style></head><body>
<h1>${esc(shortModel(h.model))}</h1>
<p class="muted">${h.org ? `${esc(h.org)} · ` : ""}${esc(SCORECARD_COPY.gradedBy(h.engine, h.grader ?? null))} · ${esc(SCORECARD_COPY.protocol(report.probes.length, h.k))} · ${esc(fmtTs(h.created))}</p>
<p class="faint">${esc(SCORECARD_COPY.scorer(h.scorer_version ?? null))}${h.seed != null ? ` · ${esc(SCORECARD_COPY.seed(h.seed))}` : ""}${h.scaffold && h.scaffold !== "baseline" ? ` · ${esc(SCORECARD_COPY.scaffold(h.scaffold))}` : ""}${h.harness && h.harness !== "single" ? ` · ${esc(SCORECARD_COPY.harness(h.harness))}` : ""}</p>
${verdict}
<div class="tiles">
  <div class="card"><span class="faint">${esc(SCORECARD_COPY.reliability)}</span><b>${pct(report.overall.pass_k_rate)}</b><span class="faint">${esc(SCORECARD_COPY.reliabilitySub(h.k))}</span></div>
  <div class="card"><span class="faint">${esc(SCORECARD_COPY.average)}</span><b>${pct(report.overall.mean_rate)}</b><span class="faint">${esc(SCORECARD_COPY.averageSubWithGap(gapPp))}</span></div>
</div>
<h2>${esc(SCORECARD_COPY.byCategory)}</h2>${categories}
<h2>${esc(SCORECARD_COPY.byAxis)}</h2>${axes}
<p class="faint">${esc(SCORECARD_COPY.axesNote)}</p>
<h2>${esc(SCORECARD_COPY.failures)}</h2>${failures}
</body></html>`;
}
