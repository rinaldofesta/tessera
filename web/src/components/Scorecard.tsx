import { useState } from "react";
import { GapBar } from "@/components/viz/GapBar";
import { SectionLabel } from "@/components/viz/SectionLabel";
import { StatTile } from "@/components/viz/StatTile";
import { VerdictBadge, verdictOf } from "@/components/viz/VerdictBadge";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { fmtTs, pct, shortModel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Probe, Report } from "@/types";
import { CONFLICT, SCORECARD_COPY as C, conflictLabel } from "@/copy";

function whyFailed(p: Probe, e: Probe["failures"][number]): string {
  if (p.expected_behavior === "refuse" && !e.refusal_ok) return C.whyRefuseMissed;
  if (p.expected_behavior === "refuse" && e.refusal_ok && !e.provenance_ok) return C.whyRefusalProvenance;
  if (!e.accuracy_ok) return C.whyWrongAnswer;
  if (!e.provenance_ok) return C.whyProvenance;
  return C.whyGeneric;
}

export function Scorecard({ report }: { report: Report }) {
  const h = report.header;
  const failed = report.probes.filter((p) => !p.pass_k);
  const [open, setOpen] = useState<string | null>(failed[0]?.probe_id ?? null);
  const failedCats = report.categories.filter((c) => c.pass_k_rate < 1);
  const reliable = failedCats.length === 0;

  return (
    <div className="space-y-5 text-[13px]">
      {/* header */}
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="font-mono text-xs">{shortModel(h.model)}</Badge>
          <span className="text-xs text-muted-foreground">
            {C.gradedBy(h.engine, h.grader ?? null)}
            {h.org ? ` · ${h.org}` : ""} · {C.protocol(report.probes.length, h.k)} · {fmtTs(h.created)}
          </span>
        </div>
        <p className="mt-1 text-[11px] text-faint">
          {C.scorer(h.scorer_version ?? null)}
          {h.seed ? ` · ${C.seed(h.seed)}` : ""}
          {h.scaffold && h.scaffold !== "baseline" ? ` · ${C.scaffold(h.scaffold)}` : ""}
          {h.harness && h.harness !== "single" ? ` · ${C.harness(h.harness)}` : ""}
        </p>
      </div>

      {/* verdict */}
      <Card
        className={cn(
          "px-4 py-3 text-[13px] font-medium",
          reliable
            ? "border-verdict-reliable/45 text-verdict-reliable"
            : "border-verdict-unreliable/45 text-verdict-unreliable",
        )}
      >
        {reliable
          ? C.reliableVerdict(h.k)
          : C.notReliableVerdict(failedCats.map((c) => conflictLabel(c.key)).join(", "))}
      </Card>

      {/* overall */}
      <div className="grid grid-cols-2 gap-2">
        <StatTile label={C.reliability} value={pct(report.overall.pass_k_rate)} sub={C.reliabilitySub(h.k)} />
        <StatTile label={C.average} value={pct(report.overall.mean_rate)} sub={C.averageSub} />
      </div>

      {/* by conflict type */}
      <div>
        <SectionLabel>{C.byCategory}</SectionLabel>
        <div className="space-y-3">
          {report.categories.map((c) => {
            const info = CONFLICT[c.key] ?? { behavior: "?", desc: "" };
            return (
              <div key={c.key}>
                <div className="flex items-center gap-3">
                  <span className="w-44 shrink-0 truncate text-xs text-foreground">{conflictLabel(c.key)}</span>
                  <div className="min-w-0 flex-1">
                    <GapBar passK={c.pass_k_rate} mean={c.mean_rate} k={h.k} />
                  </div>
                  <span className="w-10 shrink-0 text-right text-xs font-bold tabular-nums">{pct(c.pass_k_rate)}</span>
                  <span className="hidden w-16 shrink-0 text-right text-[11px] tabular-nums text-muted-foreground sm:inline">
                    {C.meanShort(pct(c.mean_rate))}
                  </span>
                  <VerdictBadge verdict={verdictOf(c.pass_k_rate, c.mean_rate)} />
                </div>
                <div className="pl-[11.75rem] text-[11px] text-faint">
                  {C.categoryMeta(c.key, info.behavior, info.desc)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* axes */}
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
        <StatTile label={C.axisAccuracy} value={pct(report.axes.accuracy_rate)} sub={C.axisAccuracySub(report.axes.n_answer_epochs)} />
        <StatTile label={C.axisProvenance} value={pct(report.axes.provenance_rate)} sub={C.axisProvenanceSub(report.axes.n_total_epochs)} />
        <StatTile label={C.axisRefusal} value={pct(report.axes.refusal_rate)} sub={C.axisRefusalSub(report.axes.n_refuse_epochs)} />
        {report.axes.answer_format_rate != null && (
          <StatTile label={C.axisFormat} value={pct(report.axes.answer_format_rate)} sub={C.axisFormatSub} />
        )}
      </div>
      <p className="text-[11px] text-faint">{C.axesNote}</p>

      {/* failures */}
      <div>
        <SectionLabel>{C.failures}</SectionLabel>
        {!failed.length ? (
          <div className="text-xs text-muted-foreground">{C.noFailures(report.probes.length)}</div>
        ) : (
          failed.map((p) => (
            <Card key={p.probe_id} className="mb-2 overflow-hidden p-0">
              <button
                onClick={() => setOpen(open === p.probe_id ? null : p.probe_id)}
                className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs hover:bg-accent/40"
              >
                <span className="flex items-center gap-2 font-semibold">
                  <VerdictBadge verdict={p.epochs_passed > 0 ? "inconsistent" : "unreliable"} />
                  {p.probe_id} · {conflictLabel(p.conflict_type)}
                </span>
                <span className="shrink-0 text-muted-foreground">
                  {C.probesPassed(p.epochs_passed, p.epochs_total)} {open === p.probe_id ? "▾" : "▸"}
                </span>
              </button>
              {open === p.probe_id && (
                <div className="space-y-2 border-t border-border px-3 py-2 text-xs">
                  {p.failures[0] && (
                    <div>
                      <span className="text-muted-foreground">{C.question} </span>
                      {p.failures[0].question}
                    </div>
                  )}
                  <div>
                    <span className="text-muted-foreground">{C.expected} </span>
                    {p.expected_behavior === "refuse" ? C.expectRefuse : C.expectAnswer}
                  </div>
                  {p.failures.map((e) => (
                    <div key={e.epoch} className="border-l-2 border-verdict-unreliable/55 pl-3">
                      <div className="font-semibold">{C.repeatFailed(e.epoch, whyFailed(p, e))}</div>
                      <blockquote className="italic text-muted-foreground">"{e.answer}"</blockquote>
                      <div className="text-[11px] text-faint">
                        {C.consulted(e.consulted.join(", ") || C.none)}
                        {e.missing.length > 0 && (
                          <>
                            {" "}· {C.missing} <b className="text-foreground">{e.missing.join(", ")}</b>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
