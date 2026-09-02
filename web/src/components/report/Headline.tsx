import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { VerdictMosaic, tilesFrom } from "@/components/VerdictMosaic";
import { GapBar, gapPoints } from "@/components/viz/GapBar";
import { StatTile } from "@/components/viz/StatTile";
import { GAP_COPY, REPORT_COPY } from "@/copy";
import { fmtTs, pct } from "@/lib/format";
import { rerunHref } from "@/lib/rerun";
import { cn } from "@/lib/utils";
import type { Run } from "@/types";

const VERDICT_COLOR = {
  reliable: "text-verdict-reliable",
  inconsistent: "text-verdict-inconsistent",
  unreliable: "text-verdict-unreliable",
} as const;

function sentenceParts(sentence: string): [string, string] {
  const end = sentence.indexOf(".");
  return end < 0 ? [sentence, ""] : [sentence.slice(0, end + 1), sentence.slice(end + 1).trim()];
}

interface HeadlineProps {
  run: Run;
  suiteLabel: string;
  onSave: () => void;
  onCopy: () => void;
  onCompare: () => void;
  onArchive: () => void;
}

export function Headline({ run, suiteLabel, onSave, onCopy, onCompare, onArchive }: HeadlineProps) {
  const report = run.report!;
  const verdict = run.verdict!;
  const [clause, rest] = sentenceParts(verdict.sentence);
  const gap = gapPoints(verdict.pass_k_rate, verdict.mean_rate);
  return (
    <section className="report-headline grid gap-8 lg:grid-cols-[minmax(0,1fr)_auto]">
      <div className="min-w-0">
        <p className="font-mono text-[11px] uppercase tracking-wider text-faint">
          {suiteLabel} · {run.request.model} · {run.request.k} repeats · {fmtTs(run.created_at)}
        </p>
        <h1 className={cn("mt-2 font-display text-4xl font-bold tracking-tight", VERDICT_COLOR[verdict.label])}>
          {clause}
        </h1>
        {rest && <p className="mt-2 max-w-2xl text-base text-foreground">{rest}</p>}

        <div className="mt-6">
          <GapBar passK={verdict.pass_k_rate} mean={verdict.mean_rate} k={run.request.k} />
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
            <span><i className="mr-1.5 inline-block size-2 rounded-full bg-primary" />{GAP_COPY.rightEveryTime} {pct(verdict.pass_k_rate)}</span>
            <span><i className="mr-1.5 inline-block size-2 rounded-full bg-verdict-inconsistent" />{GAP_COPY.onlySometimes} +{gap} pp</span>
            <span><i className="mr-1.5 inline-block size-2 rounded-full border border-line bg-raised" />{GAP_COPY.never}</span>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3">
          <StatTile label={`pass^${run.request.k} — ${GAP_COPY.rightEveryTime}`} value={pct(verdict.pass_k_rate)} />
          <StatTile label="mean — right on average" value={pct(verdict.mean_rate)} />
        </div>

        <div className="report-actions mt-5 flex flex-wrap gap-2">
          <Button onClick={onSave}>{REPORT_COPY.save}</Button>
          <Button variant="outline" onClick={onCopy}>{REPORT_COPY.copySummary}</Button>
          <Button variant="outline" onClick={onCompare}>{REPORT_COPY.compare}</Button>
          <Button variant="outline" nativeButton={false} render={<Link role="link" to={rerunHref(run)} />}>{REPORT_COPY.runAgain}</Button>
          {run.source !== "bundled" && <Button variant="ghost" onClick={onArchive}>{run.archived ? REPORT_COPY.restore : REPORT_COPY.archive}</Button>}
        </div>
      </div>
      <div className="flex justify-center lg:justify-end">
        <VerdictMosaic questions={report.probes.length} repeats={run.request.k} tiles={tilesFrom(report)} size="lg" />
      </div>
    </section>
  );
}
