import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { tilesFrom, VerdictMosaic } from "@/components/VerdictMosaic";
import { SectionLabel } from "@/components/viz/SectionLabel";
import { StatTile } from "@/components/viz/StatTile";
import { StatusBadge } from "@/components/viz/StatusBadge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LIVE_COPY } from "@/copy";
import { useRunStatus } from "@/hooks";
import { elapsed, pct, shortModel } from "@/lib/format";
import type { Run } from "@/types";

interface LiveRunPanelProps {
  jobId: string;
  questions: number;
  repeats: number;
  model: string;
  suite: string;
  onTerminal?: (run: Run) => void;
}

/** /new's right column after launch. Honest by construction: while running it shows
 * only what the server actually reports — status, elapsed, and fixed dimensions. */
export function LiveRunPanel({ jobId, questions, repeats, model, suite, onTerminal }: LiveRunPanelProps) {
  const watch = useRunStatus(jobId);
  const run = watch.run;
  const status = run?.status ?? "running";
  const [startedAt] = useState(Date.now);
  const [, tick] = useState(0);

  useEffect(() => {
    if (status !== "queued" && status !== "running") return;
    const timer = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(timer);
  }, [status]);

  useEffect(() => {
    if (watch.terminal && run) onTerminal?.(run);
  }, [onTerminal, run, watch.terminal]);

  const tiles = useMemo(() => (run?.report ? tilesFrom(run.report) : undefined), [run?.report]);
  // Once the report loads, its own dimensions are the honest source of truth — questions/repeats
  // are only a pre-launch estimate, and the wizard on the left stays editable after launch, so
  // they can drift from what the running job actually used.
  const mosaicQuestions = run?.report?.probes.length ?? questions;
  const mosaicRepeats = run?.report?.probes[0]?.epochs_total ?? run?.report?.header.k ?? repeats;

  return (
    <Card className="space-y-4 p-4">
      <SectionLabel>
        {status === "completed"
          ? LIVE_COPY.doneTitle(shortModel(model))
          : LIVE_COPY.liveTitle(shortModel(model), suite)}
      </SectionLabel>

      <div className="flex items-center gap-3">
        <StatusBadge status={status} />
        {(status === "queued" || status === "running") && (
          <span className="font-mono text-xs text-muted-foreground">{elapsed(startedAt)}</span>
        )}
      </div>

      {mosaicQuestions > 0 && (
        <VerdictMosaic questions={mosaicQuestions} repeats={mosaicRepeats} tiles={tiles} />
      )}

      {status === "completed" && run?.report && (
        <>
          {run.verdict?.sentence && <p className="text-[13px] font-medium">{run.verdict.sentence}</p>}
          <div className="grid grid-cols-2 gap-2">
            <StatTile label={LIVE_COPY.reliability} value={pct(run.report.overall.pass_k_rate)} sub={LIVE_COPY.reliabilitySub(run.report.header.k)} />
            <StatTile label={LIVE_COPY.average} value={pct(run.report.overall.mean_rate)} sub={LIVE_COPY.averageSub} />
          </div>
          <Button variant="outline" size="sm" nativeButton={false} render={<Link role="link" to={`/reports/${jobId}`} />}>
            {LIVE_COPY.openDetail}
          </Button>
        </>
      )}

      {(status === "failed" || status === "interrupted") && (watch.error || run?.error) && (
        <Alert variant="destructive">
          <AlertDescription className="break-words font-mono text-xs">{watch.error ?? run?.error}</AlertDescription>
        </Alert>
      )}
    </Card>
  );
}
