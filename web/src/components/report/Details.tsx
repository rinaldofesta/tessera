import { useLocation } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { CategoryBars } from "@/components/viz/CategoryBars";
import { SectionLabel } from "@/components/viz/SectionLabel";
import { StatTile } from "@/components/viz/StatTile";
import { VerdictBadge, verdictOf, whyFailed } from "@/components/viz/VerdictBadge";
import { REPORT_COPY, conflictLabel } from "@/copy";
import { pct } from "@/lib/format";
import type { Run } from "@/types";

export function Details({ run }: { run: Run }) {
  const { hash } = useLocation();
  const report = run.report!;
  const receipt = run.receipt;
  const failed = report.probes.filter((probe) => !probe.pass_k);
  return (
    <details className="report-details mt-8 border-t border-line pt-4" open={hash === "#details"}>
      <summary className="cursor-pointer font-display text-base font-semibold text-foreground">{REPORT_COPY.details}</summary>
      <div className="mt-6 space-y-8">
        <section>
          <SectionLabel>{REPORT_COPY.categories}</SectionLabel>
          <div className="grid gap-5 md:grid-cols-2">
            {report.categories.map((category) => (
              <div key={category.key} className="rounded-lg border border-line bg-panel p-3">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{conflictLabel(category.key)}</span>
                  <VerdictBadge verdict={verdictOf(category.pass_k_rate, category.mean_rate)} />
                </div>
                <CategoryBars groups={[{ key: category.key, label: `pass^${run.request.k}`, series: [{ id: "run", label: run.request.model, color: "var(--series-a)", value: category.pass_k_rate }] }]} />
              </div>
            ))}
          </div>
        </section>

        <section>
          <SectionLabel>{REPORT_COPY.axes}</SectionLabel>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            <StatTile label={REPORT_COPY.axisAccuracy} value={pct(report.axes.accuracy_rate)} sub={REPORT_COPY.axisAccuracySub(report.axes.n_answer_epochs)} />
            <StatTile label={REPORT_COPY.axisProvenance} value={pct(report.axes.provenance_rate)} sub={REPORT_COPY.axisProvenanceSub(report.axes.n_total_epochs)} />
            <StatTile label={REPORT_COPY.axisRefusal} value={pct(report.axes.refusal_rate)} sub={REPORT_COPY.axisRefusalSub(report.axes.n_refuse_epochs)} />
          </div>
        </section>

        <section>
          <SectionLabel>{REPORT_COPY.failures}</SectionLabel>
          {!failed.length ? <p className="text-sm text-muted-foreground">{REPORT_COPY.noFailures(report.probes.length)}</p> : failed.map((probe) => (
            <Card key={probe.probe_id} className="mb-3 p-4">
              <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                <VerdictBadge verdict={verdictOf(0, probe.mean_pass)} />
                <span>{probe.probe_id} · {conflictLabel(probe.conflict_type)}</span>
                <span className="ml-auto text-xs text-faint">{REPORT_COPY.probesPassed(probe.epochs_passed, probe.epochs_total)}</span>
              </div>
              {probe.failures.map((failure) => (
                <div key={failure.epoch} className="mt-3 border-l-2 border-verdict-unreliable/55 pl-3 text-sm">
                  <p className="font-semibold">{REPORT_COPY.repeatFailed(failure.epoch, whyFailed(probe.expected_behavior, failure))}</p>
                  <p className="mt-1 text-muted-foreground">{failure.question}</p>
                  <blockquote className="mt-1 italic text-muted-foreground">“{failure.answer}”</blockquote>
                  <p className="mt-1 text-xs text-faint">{REPORT_COPY.consulted(failure.consulted.join(", ") || REPORT_COPY.none)}{failure.missing.length ? ` · ${REPORT_COPY.missing} ${failure.missing.join(", ")}` : ""}</p>
                </div>
              ))}
            </Card>
          ))}
        </section>

        {run.diagnostics.length > 0 && <section><SectionLabel>{REPORT_COPY.diagnostics}</SectionLabel><ul className="space-y-1 text-xs text-muted-foreground">{run.diagnostics.map((item) => <li key={`${item.kind}-${item.signature}`}>{item.kind} · {item.signature} · {item.count}</li>)}</ul></section>}

        <section>
          <SectionLabel>{REPORT_COPY.receipt}</SectionLabel>
          <dl className="grid gap-2 rounded-lg border border-line bg-panel p-4 font-mono text-xs md:grid-cols-[10rem_minmax(0,1fr)]">
            <dt className="text-faint">{REPORT_COPY.scorerVersion}</dt><dd className="break-all">{receipt?.protocol.scorer_version ?? report.header.scorer_version ?? "—"}</dd>
            <dt className="text-faint">{REPORT_COPY.scaffold}</dt><dd className="break-all">{receipt?.protocol.scaffold ?? run.request.scaffold}</dd>
            <dt className="text-faint">{REPORT_COPY.seed}</dt><dd>{receipt?.protocol.seed ?? run.request.seed}</dd>
            <dt className="text-faint">{REPORT_COPY.protocolHash}</dt><dd className="break-all">{receipt?.protocol_hash ?? "—"}</dd>
            <dt className="text-faint">{REPORT_COPY.logPath}</dt><dd className="break-all">{run.paths.log ?? "—"}</dd>
          </dl>
        </section>
      </div>
    </details>
  );
}
