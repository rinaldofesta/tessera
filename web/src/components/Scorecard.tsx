import { useState } from "react";
import { GradeToken, Metric, MeterBar, SectionLabel } from "@/components/term";
import { fmtTs, pct } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Probe, Report } from "@/types";
import { CONFLICT, conflictLabel } from "../copy";

function whyFailed(p: Probe, e: Probe["failures"][number]): string {
  if (p.expected_behavior === "refuse" && !e.refusal_ok) return "committed to an answer when it should have refused";
  if (p.expected_behavior === "refuse" && e.refusal_ok && !e.provenance_ok)
    return "refused correctly, but missed required sources";
  if (!e.accuracy_ok) return "wrong answer";
  if (!e.provenance_ok) return "right answer, but missed required sources";
  return "failed a reliability check";
}

export function Scorecard({ report }: { report: Report }) {
  const h = report.header;
  const failed = report.probes.filter((p) => !p.pass_k);
  const [open, setOpen] = useState<string | null>(failed[0]?.probe_id ?? null);
  const failedCats = report.categories.filter((c) => c.pass_k_rate < 1);
  const reliable = failedCats.length === 0;

  return (
    <div className="space-y-4 text-[13px]">
      {/* header */}
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="border border-foreground px-1.5 py-0.5 text-xs font-bold">{h.model}</span>
        <span className="text-[11px] text-muted-foreground">
          {h.engine === "llm" ? `scored by an ai grader${h.grader ? ` (${h.grader})` : ""}` : "scored by fixed rules"}
          {h.org ? ` · dataset: ${h.org}` : ""} · {report.probes.length} questions × {h.k} repeats · {fmtTs(h.created)}
        </span>
      </div>

      <div className="text-[10px] text-muted-foreground">
        run details: scorer {h.scorer_version}
        {h.seed ? ` · dataset variant seed ${h.seed}` : ""}
        {h.scaffold && h.scaffold !== "baseline" ? ` · prompt scaffold: ${h.scaffold}` : ""}
        {h.harness && h.harness !== "single" ? ` · harness: ${h.harness} (how model calls were dispatched)` : ""}
      </div>

      {/* verdict */}
      <div className={cn("border px-3 py-2 text-xs", reliable ? "border-border" : "border-foreground")}>
        {reliable ? (
          <>
            <b>✓ RELIABLE</b> — correct behavior in all {h.k} repeats of every probe.
          </>
        ) : (
          <>
            <b>✗ NOT RELIABLE on {failedCats.map((c) => c.key).join(", ")}</b> — it does not behave
            correctly every time; a single average score would hide this.
          </>
        )}
      </div>

      {/* overall */}
      <div className="grid grid-cols-2 gap-2">
        <Metric label="reliability" value={pct(report.overall.pass_k_rate)} sub={`passed all ${h.k} repeats — pass^${h.k}`} />
        <Metric label="average" value={pct(report.overall.mean_rate)} sub="mean rate across repeats" />
      </div>

      {/* by conflict type */}
      <div>
        <SectionLabel>reliability by question type</SectionLabel>
        <div className="space-y-2.5">
          {report.categories.map((c) => {
            const info = CONFLICT[c.key] ?? { behavior: "?", desc: "" };
            return (
              <div key={c.key}>
                <div className="flex items-center gap-2">
                  <span className="w-40 shrink-0 truncate text-xs">{conflictLabel(c.key)}</span>
                  <div className="min-w-0 flex-1">
                    <MeterBar value={c.pass_k_rate} flaky={c.flaky} />
                  </div>
                  <span className="w-10 shrink-0 text-right text-xs font-bold tabular-nums">
                    {pct(c.pass_k_rate)}
                  </span>
                  <span className="hidden w-20 shrink-0 text-right text-[11px] tabular-nums text-muted-foreground sm:inline">
                    mean {pct(c.mean_rate)}
                  </span>
                  <GradeToken passK={c.pass_k_rate} flaky={c.flaky} />
                </div>
                <div className="pl-[10.5rem] text-[11px] text-muted-foreground">
                  {c.key} · expect {info.behavior} — {info.desc}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* axes */}
      <div className="grid grid-cols-3 gap-2">
        <Metric label="right answers" value={pct(report.axes.accuracy_rate)} sub={`accuracy · ${report.axes.n_answer_epochs} answer-epochs`} />
        <Metric label="cited the right sources" value={pct(report.axes.provenance_rate)} sub={`provenance · ${report.axes.n_total_epochs} epochs`} />
        <Metric label="refused when it should" value={pct(report.axes.refusal_rate)} sub={`refusal · ${report.axes.n_refuse_epochs} refuse-epochs`} />
        {report.axes.answer_format_rate != null && (
          <Metric label="answered in the expected format" value={pct(report.axes.answer_format_rate)} sub="the ANSWER: <value> contract" />
        )}
      </div>
      <p className="text-[11px] text-muted-foreground">
        denominators differ — an axis only counts where it applies. "cited the right sources"
        is read from the agent's real tool calls, never judged by a model.
      </p>

      {/* failures */}
      <div>
        <SectionLabel>failures</SectionLabel>
        {!failed.length ? (
          <div className="text-xs text-muted-foreground">
            none — all {report.probes.length} probes passed every repeat.
          </div>
        ) : (
          failed.map((p) => (
            <div key={p.probe_id} className="mb-1 border border-border">
              <button
                onClick={() => setOpen(open === p.probe_id ? null : p.probe_id)}
                className="flex w-full items-center justify-between gap-2 px-2 py-1.5 text-left text-xs hover:bg-muted"
              >
                <span className="font-bold">✗ {p.probe_id} · {conflictLabel(p.conflict_type)}</span>
                <span className="shrink-0 text-muted-foreground">
                  {p.epochs_passed}/{p.epochs_total} passed {open === p.probe_id ? "▾" : "▸"}
                </span>
              </button>
              {open === p.probe_id && (
                <div className="space-y-2 border-t border-border px-2 py-2 text-xs">
                  {p.failures[0] && (
                    <div>
                      <span className="text-muted-foreground">Q: </span>
                      {p.failures[0].question}
                    </div>
                  )}
                  <div>
                    <span className="text-muted-foreground">expected: </span>
                    {p.expected_behavior === "refuse" ? "refuse and escalate" : "answer with sources"}
                  </div>
                  {p.failures.map((e) => (
                    <div key={e.epoch} className="border-l-2 border-foreground pl-2">
                      <div className="font-bold">
                        repeat {e.epoch} — {whyFailed(p, e)}
                      </div>
                      <blockquote className="italic text-muted-foreground">"{e.answer}"</blockquote>
                      <div className="text-[11px] text-muted-foreground">
                        consulted: {e.consulted.join(", ") || "(none)"}
                        {e.missing.length > 0 && (
                          <>
                            {" "}· missing: <b className="text-foreground">{e.missing.join(", ")}</b>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
