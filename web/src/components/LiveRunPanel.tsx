import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { tilesFrom, VerdictMosaic } from "@/components/VerdictMosaic";
import { SectionLabel } from "@/components/viz/SectionLabel";
import { StatTile } from "@/components/viz/StatTile";
import { StatusBadge } from "@/components/viz/StatusBadge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LIVE_COPY, conflictLabel } from "@/copy";
import { useRunStatus } from "@/hooks";
import { pct, shortModel } from "@/lib/format";

function elapsedLabel(from: number): string {
  const seconds = Math.floor((Date.now() - from) / 1000);
  return seconds < 60
    ? `${seconds}s`
    : `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
}

interface LiveRunPanelProps {
  jobId: string;
  questions: number;
  repeats: number;
  model: string;
  suite: string;
}

/** /new's right column after launch. Honest by construction: while running it shows
 * only what the server actually reports — status, elapsed, and fixed dimensions. */
export function LiveRunPanel({ jobId, questions, repeats, model, suite }: LiveRunPanelProps) {
  const run = useRunStatus(jobId);
  const [, tick] = useState(0);

  useEffect(() => {
    if (run.status !== "running") return;
    const timer = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(timer);
  }, [run.status]);

  const tiles = useMemo(() => (run.report ? tilesFrom(run.report) : undefined), [run.report]);
  const failedCats = run.report?.categories.filter((category) => category.pass_k_rate < 1) ?? [];

  return (
    <Card className="space-y-4 p-4">
      <SectionLabel>
        {run.status === "done"
          ? LIVE_COPY.doneTitle(shortModel(model))
          : LIVE_COPY.liveTitle(shortModel(model), suite)}
      </SectionLabel>

      <div className="flex items-center gap-3">
        <StatusBadge status={run.status} />
        {run.status === "running" && (
          <span className="font-mono text-xs text-muted-foreground">{elapsedLabel(run.startedAt)}</span>
        )}
      </div>

      {questions > 0 && <VerdictMosaic questions={questions} repeats={repeats} tiles={tiles} />}

      {run.status === "done" && run.report && (
        <>
          <p className="text-[13px] font-medium">
            {failedCats.length === 0
              ? LIVE_COPY.reliable(run.report.header.k)
              : LIVE_COPY.notReliable(failedCats.map((category) => conflictLabel(category.key)).join(", "))}
          </p>
          <div className="grid grid-cols-2 gap-2">
            <StatTile label={LIVE_COPY.reliability} value={pct(run.report.overall.pass_k_rate)} sub={LIVE_COPY.reliabilitySub(run.report.header.k)} />
            <StatTile label={LIVE_COPY.average} value={pct(run.report.overall.mean_rate)} sub={LIVE_COPY.averageSub} />
          </div>
          <Button variant="outline" size="sm" nativeButton={false} render={<Link role="link" to={`/runs/${jobId}`} />}>
            {LIVE_COPY.openDetail}
          </Button>
        </>
      )}

      {run.status === "error" && run.error && (
        <Alert variant="destructive">
          <AlertDescription className="break-words font-mono text-xs">{run.error}</AlertDescription>
        </Alert>
      )}
    </Card>
  );
}
