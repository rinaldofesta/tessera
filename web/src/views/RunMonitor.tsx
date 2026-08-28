import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/api";
import { VerdictMosaic, type TileState } from "@/components/VerdictMosaic";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { MONITOR_COPY } from "@/copy";
import type { Report, RunStatus } from "@/types";

const MAX_POLL_FAILURES = 5;

function elapsed(from: number): string {
  const seconds = Math.floor((Date.now() - from) / 1000);
  return seconds < 60
    ? `${seconds}s`
    : `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
}

/** Lay out repeats as rows so each failed epoch lands on its actual tile. */
function tilesFrom(report: Report): TileState[] {
  const repeats = report.probes[0]?.epochs_total ?? report.header.k;
  return Array.from({ length: repeats }, (_, repeat) =>
    report.probes.map((probe) =>
      probe.failures.some((failure) => failure.epoch === repeat + 1) ? "fail" : "pass",
    ),
  ).flat();
}

interface RunConfiguration {
  model: string;
  suite: string;
  grading: string;
  questions: number;
  repeats: number;
}

export default function RunMonitor() {
  const { id = "" } = useParams();
  const [status, setStatus] = useState<RunStatus["status"]>("running");
  const [report, setReport] = useState<Report | null>(null);
  const [configuration, setConfiguration] = useState<RunConfiguration | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [, forceTick] = useState(0);
  const startedAt = useRef(Date.now());

  useEffect(() => {
    let poller: ReturnType<typeof setInterval> | null = null;
    let failures = 0;
    let active = true;

    startedAt.current = Date.now();
    setStatus("running");
    setReport(null);
    setConfiguration(null);
    setError(null);

    const stopPolling = () => {
      if (poller) {
        clearInterval(poller);
        poller = null;
      }
    };

    const apply = (next: RunStatus) => {
      if (!active) return;
      setStatus(next.status);
      if (next.report) setReport(next.report);
      if (next.error) setError(next.error);
      if (next.status !== "running") stopPolling();
    };

    const source = api.watchRun(id);

    // RunStatus has no in-flight report, so these read-only endpoints provide the
    // fixed dimensions needed to render honest pending tiles from the first frame.
    Promise.all([api.listRuns(), api.evalSetup()])
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

    source.onmessage = (event) => {
      const next = JSON.parse(event.data) as {
        status: RunStatus["status"];
        error: string | null;
      };

      setStatus(next.status);
      if (next.error) setError(next.error);
      if (next.status !== "running") {
        source.close();
        api.getRun(id).then(apply).catch(() => {});
      }
    };
    source.onerror = () => {
      source.close();
      if (poller) return;

      poller = setInterval(() => {
        api
          .getRun(id)
          .then((next) => {
            failures = 0;
            apply(next);
          })
          .catch(() => {
            failures += 1;
            if (failures >= MAX_POLL_FAILURES) stopPolling();
          });
      }, 2000);
    };

    const ticker = setInterval(() => forceTick((tick) => tick + 1), 1000);
    return () => {
      active = false;
      source.close();
      stopPolling();
      clearInterval(ticker);
    };
  }, [id]);

  const questions = report?.probes.length ?? configuration?.questions ?? 0;
  const repeats =
    report?.probes[0]?.epochs_total ?? report?.header.k ?? configuration?.repeats ?? 0;
  const tiles = useMemo(() => (report ? tilesFrom(report) : undefined), [report]);
  const model = report?.header.model ?? configuration?.model;
  const suite = report?.header.org ?? configuration?.suite;
  const grading = report?.header.engine ?? configuration?.grading;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-1 font-display text-2xl font-bold tracking-tight">
        {report ? MONITOR_COPY.doneTitle(report.header.model) : MONITOR_COPY.runningTitle}
      </h1>

      <div className="mb-5 flex items-center gap-3">
        <Badge
          variant="outline"
          className={
            status === "error"
              ? "border-[var(--verdict-unreliable)]/55 text-[var(--verdict-unreliable)]"
              : status === "done"
                ? "border-[var(--verdict-reliable)]/55 text-[var(--verdict-reliable)]"
                : "border-[var(--primary)]/55 text-[var(--primary)]"
          }
        >
          {MONITOR_COPY.status[status]}
        </Badge>
        {status === "running" && (
          <span className="text-sm text-[var(--muted-foreground)]">
            {MONITOR_COPY.elapsed(elapsed(startedAt.current))}
          </span>
        )}
      </div>

      {questions > 0 && (
        <div className="mb-6">
          <VerdictMosaic questions={questions} repeats={repeats} tiles={tiles} />
        </div>
      )}

      {(model || suite || grading) && (
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
