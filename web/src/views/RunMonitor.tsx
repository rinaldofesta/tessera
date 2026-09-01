import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/api";
import { Scorecard } from "@/components/Scorecard";
import { tilesFrom, VerdictMosaic } from "@/components/VerdictMosaic";
import { StatusBadge } from "@/components/viz/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { MONITOR_COPY } from "@/copy";
import { useRunStatus } from "@/hooks";
import { downloadReport } from "@/lib/exportReport";
import { elapsed } from "@/lib/format";

interface RunConfiguration {
  model: string;
  suite: string;
  grading: string;
  questions: number;
  repeats: number;
}

export default function RunMonitor() {
  const { id = "" } = useParams();
  const { status, report, error, startedAt } = useRunStatus(id);
  const [configuration, setConfiguration] = useState<RunConfiguration | null>(null);
  const [, forceTick] = useState(0);

  useEffect(() => {
    let active = true;

    setConfiguration(null);

    // RunStatus has no in-flight report, so these read-only endpoints provide the
    // fixed dimensions needed to render honest pending tiles from the first frame.
    Promise.all([api.listRuns(true), api.evalSetup()])
      .then(([runs, setup]) => {
        if (!active) return;
        const run = runs.find((candidate) => candidate.id === id);
        if (!run) return;
        setConfiguration({
          model: run.model,
          suite: run.org,
          grading: run.judge,
          questions: setup.suites.find((suite) => suite.id === run.org)?.questions ?? 0,
          repeats: run.epochs,
        });
      })
      .catch(() => {});

    return () => { active = false; };
  }, [id]);

  useEffect(() => {
    const ticker = setInterval(() => forceTick((tick) => tick + 1), 1000);
    return () => clearInterval(ticker);
  }, []);

  const questions = report?.probes.length ?? configuration?.questions ?? 0;
  const repeats =
    report?.probes[0]?.epochs_total ?? report?.header.k ?? configuration?.repeats ?? 0;
  const tiles = useMemo(() => (report ? tilesFrom(report) : undefined), [report]);
  const model = report?.header.model ?? configuration?.model;
  const suite = report?.header.org ?? configuration?.suite;
  const grading = report?.header.engine ?? configuration?.grading;

  const exportRun = (format: "html" | "json") => {
    if (!report) return;
    try {
      downloadReport(report, format);
    } catch {
      toast.error(MONITOR_COPY.exportFailed);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-1 font-display text-2xl font-bold tracking-tight">
        {report ? MONITOR_COPY.doneTitle(report.header.model) : MONITOR_COPY.runningTitle}
      </h1>

      <div className="mb-5 flex items-center gap-3">
        <StatusBadge status={status} />
        {status === "running" && (
          <span className="text-sm text-[var(--muted-foreground)]">
            {MONITOR_COPY.elapsed(elapsed(startedAt))}
          </span>
        )}
      </div>

      {questions > 0 && (
        <div className="mb-6">
          <VerdictMosaic questions={questions} repeats={repeats} tiles={tiles} size="lg" />
        </div>
      )}

      {report && (
        <>
          <div className="mb-4 flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportRun("html")}
            >
              {MONITOR_COPY.exportHtml}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportRun("json")}
            >
              {MONITOR_COPY.exportJson}
            </Button>
          </div>
          <Card className="p-5">
            <Scorecard report={report} />
          </Card>
        </>
      )}

      {!report && (model || suite || grading) && (
        <Card className="p-4">
          <dl className="text-[13px]">
            <div className="flex justify-between py-1.5">
              <dt className="text-[var(--muted-foreground)]">{MONITOR_COPY.model}</dt>
              <dd className="font-mono">{model ?? "—"}</dd>
            </div>
            <Separator />
            <div className="flex justify-between py-1.5">
              <dt className="text-[var(--muted-foreground)]">{MONITOR_COPY.suite}</dt>
              <dd className="font-mono">{suite ?? "—"}</dd>
            </div>
            <Separator />
            <div className="flex justify-between py-1.5">
              <dt className="text-[var(--muted-foreground)]">{MONITOR_COPY.grading}</dt>
              <dd className="font-mono">{grading ?? "—"}</dd>
            </div>
          </dl>
        </Card>
      )}

      {status === "error" && error && (
        <Card className="mt-4 border-[var(--verdict-unreliable)]/45 p-4">
          <p className="mb-2 text-[13px] font-semibold">{MONITOR_COPY.failed}</p>
          <p className="break-words font-mono text-[12px] text-[var(--muted-foreground)]">
            {error}
          </p>
        </Card>
      )}

      {status === "running" && (
        <p className="mt-5 border-l-2 border-[var(--primary)] pl-4 text-sm text-[var(--muted-foreground)]">
          {MONITOR_COPY.safeToLeave}
        </p>
      )}

      <div className="mt-6 flex gap-3">
        <Button variant="ghost" nativeButton={false} render={<Link to="/runs" />}>
          {MONITOR_COPY.allRuns}
        </Button>
        <Button variant="ghost" nativeButton={false} render={<Link to="/new" />}>
          {MONITOR_COPY.newRun}
        </Button>
      </div>
    </div>
  );
}
