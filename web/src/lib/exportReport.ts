import { SCORECARD_COPY, conflictLabel } from "@/copy";
import { pct, shortModel } from "@/lib/format";
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

export function reportFilename(report: Report, ext: "html" | "json"): string {
  const clean = (s: string) => s.replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "");
  const date = clean(report.header.created.slice(0, 10)) || "undated";
  return `tessera-${clean(report.header.org ?? "run")}-${clean(shortModel(report.header.model))}-${date}.${ext}`;
}

export function exportReportJson(report: Report): string {
  return JSON.stringify(report, null, 2);
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

function whyFailed(expected: string, f: Report["probes"][number]["failures"][number]): string {
  // Same vocabulary as the on-screen Scorecard — SCORECARD_COPY is the single source.
  if (expected === "refuse" && !f.refusal_ok) return SCORECARD_COPY.whyRefuseMissed;
  if (expected === "refuse" && f.refusal_ok && !f.provenance_ok) return SCORECARD_COPY.whyRefusalProvenance;
  if (!f.accuracy_ok) return SCORECARD_COPY.whyWrongAnswer;
  if (!f.provenance_ok) return SCORECARD_COPY.whyProvenance;
  return SCORECARD_COPY.whyGeneric;
}

function bar(passK: number, mean: number): string {
  const p = Math.min(1, Math.max(0, passK));
  const m = Math.max(Math.min(1, Math.max(0, mean)), p);
  const fill = `<i${p >= 1 - 1e-9 ? ' class="full"' : ""} style="width:${(p * 100).toFixed(2)}%"></i>`;
  const gap = `<em style="width:${((m - p) * 100).toFixed(2)}%"></em>`;
  return `<div class="bar">${fill}${gap}</div>`;
}

/** Self-contained, script-free scorecard document. Native <details> for failures. */
export function exportReportHtml(report: Report): string {
  const h = report.header;
  const failed = report.probes.filter((p) => !p.pass_k);
  const failedCats = report.categories.filter((c) => c.pass_k_rate < 1);
  const gapPp = Math.round((report.overall.mean_rate - report.overall.pass_k_rate) * 100);

  const verdict = failedCats.length === 0
    ? `<div class="card verdict-ok"><b>✓ RELIABLE</b> — correct behavior in all ${h.k} repeats of every probe.</div>`
    : `<div class="card verdict-bad"><b>✗ NOT RELIABLE on ${esc(
        failedCats.map((c) => conflictLabel(c.key)).join(", "),
      )}</b> — it does not behave correctly every time; a single average score would hide this.</div>`;

  const categories = report.categories
    .map(
      (c) => `<div class="card">
        <table><tr><td>${esc(conflictLabel(c.key))}</td>
        <td style="text-align:right"><b>${pct(c.pass_k_rate)}</b> <span class="faint">pass^${h.k} · mean ${pct(c.mean_rate)}</span></td></tr></table>
        ${bar(c.pass_k_rate, c.mean_rate)}</div>`,
    )
    .join("");

  const axes = `<div class="tiles">
    <div class="card"><span class="faint">right answers</span><b>${pct(report.axes.accuracy_rate)}</b><span class="faint">accuracy · ${report.axes.n_answer_epochs} answer-epochs</span></div>
    <div class="card"><span class="faint">cited the right sources</span><b>${pct(report.axes.provenance_rate)}</b><span class="faint">provenance · ${report.axes.n_total_epochs} epochs</span></div>
    <div class="card"><span class="faint">refused when it should</span><b>${pct(report.axes.refusal_rate)}</b><span class="faint">refusal · ${report.axes.n_refuse_epochs} refuse-epochs</span></div>
  </div>`;

  const failures = failed.length === 0
    ? `<p class="muted">none — all ${report.probes.length} probes passed every repeat.</p>`
    : failed
        .map(
          (p) => `<details class="card"><summary>✗ ${esc(p.probe_id)} · ${esc(
            conflictLabel(p.conflict_type),
          )} <span class="faint">${p.epochs_passed}/${p.epochs_total} passed</span></summary>
          ${p.failures[0] ? `<p><span class="muted">Q:</span> ${esc(p.failures[0].question)}</p>` : ""}
          <p><span class="muted">expected:</span> ${p.expected_behavior === "refuse" ? "refuse and escalate" : "answer with sources"}</p>
          ${p.failures
            .map(
              (f) => `<p><b>repeat ${f.epoch} — ${esc(whyFailed(p.expected_behavior, f))}</b></p>
              <blockquote>"${esc(f.answer)}"</blockquote>
              <p class="faint">consulted: ${esc(f.consulted.join(", ") || "(none)")}${
                f.missing.length > 0 ? ` · missing: <b>${esc(f.missing.join(", "))}</b>` : ""
              }</p>`,
            )
            .join("")}</details>`,
        )
        .join("");

  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>tessera — ${esc(shortModel(h.model))} on ${esc(h.org ?? "run")}</title><style>${CSS}</style></head><body>
<h1>${esc(shortModel(h.model))}</h1>
<p class="muted">${esc(h.org ?? "")} · ${h.engine === "llm" ? `scored by an ai grader${h.grader ? ` (${esc(h.grader)})` : ""}` : "scored by fixed rules"} · ${report.probes.length} questions × ${h.k} repeats · ${esc(h.created)}</p>
<p class="faint">${esc(h.scorer_version ? `scorer ${h.scorer_version}` : "scorer version not recorded")}${h.seed ? ` · dataset variant seed ${h.seed}` : ""}${h.scaffold && h.scaffold !== "baseline" ? ` · prompt scaffold: ${esc(h.scaffold)}` : ""}${h.harness && h.harness !== "single" ? ` · harness: ${esc(h.harness)}` : ""}</p>
${verdict}
<div class="tiles">
  <div class="card"><span class="faint">reliability</span><b>${pct(report.overall.pass_k_rate)}</b><span class="faint">passed all ${h.k} repeats — pass^${h.k}</span></div>
  <div class="card"><span class="faint">average</span><b>${pct(report.overall.mean_rate)}</b><span class="faint">mean across repeats · gap ${gapPp} pp</span></div>
</div>
<h2>reliability by question type</h2>${categories}
<h2>how it failed, by axis</h2>${axes}
<p class="faint">denominators differ — an axis only counts where it applies. "cited the right sources" is read from the agent's real tool calls, never judged by a model.</p>
<h2>failures</h2>${failures}
</body></html>`;
}
