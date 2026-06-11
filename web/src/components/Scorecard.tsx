import { useState } from "react";
import { GradeToken, Metric, MeterBar, SectionLabel } from "@/components/term";
import { fmtTs, pct } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Probe, Report } from "@/types";

const CONFLICT: Record<string, { behavior: string; desc: string }> = {
  none: { behavior: "answer", desc: "facts agree across silos — stitch them into one answer" },
  resolvable: { behavior: "answer", desc: "sources clash but a rule (newer / more authoritative) breaks the tie" },
  unresolvable: { behavior: "refuse", desc: "equal-authority sources clash, no tiebreaker — must refuse and escalate" },
  void: { behavior: "refuse", desc: "the fact is absent — must refuse, not invent it" },
};

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
          engine={h.engine}
          {h.grader ? ` grader=${h.grader}` : ""}
          {h.org ? ` org=${h.org}` : ""} · {report.probes.length} probes × {h.k} repeats · {fmtTs(h.created)}
        </span>
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
        <Metric label={`pass^${h.k} (strict)`} value={pct(report.overall.pass_k_rate)} />
        <Metric label="mean" value={pct(report.overall.mean_rate)} />
      </div>

      {/* by conflict type */}
      <div>
        <SectionLabel>pass^{h.k} by conflict type</SectionLabel>
        <div className="space-y-2.5">
          {report.categories.map((c) => {
            const info = CONFLICT[c.key] ?? { behavior: "?", desc: "" };
            return (
              <div key={c.key}>
                <div className="flex items-center gap-2">
                  <span className="w-28 shrink-0 truncate text-xs">{c.key}</span>
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
                <div className="pl-[7.5rem] text-[11px] text-muted-foreground">
                  expect {info.behavior} — {info.desc}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* axes */}
      <div className="grid grid-cols-3 gap-2">
        <Metric label="accuracy" value={pct(report.axes.accuracy_rate)} sub={`${report.axes.n_answer_epochs} answer-epochs`} />
        <Metric label="provenance" value={pct(report.axes.provenance_rate)} sub={`${report.axes.n_total_epochs} epochs · mechanical`} />
        <Metric label="refusal" value={pct(report.axes.refusal_rate)} sub={`${report.axes.n_refuse_epochs} refuse-epochs`} />
      </div>
      <p className="text-[11px] text-muted-foreground">
        denominators differ — an axis only counts where it applies. provenance is read from the
        agent's real tool calls, never judged by a model.
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
                <span className="font-bold">✗ {p.probe_id} · {p.conflict_type}</span>
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
