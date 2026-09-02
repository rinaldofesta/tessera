import { useCallback, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/api";
import { ComparePanel } from "@/components/ComparePanel";
import { LiveRunPanel } from "@/components/LiveRunPanel";
import { Details } from "@/components/report/Details";
import { Headline } from "@/components/report/Headline";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { COMPARE_COPY, REPORT_COPY } from "@/copy";
import { useAsync, useCatalog } from "@/hooks";
import { downloadReport } from "@/lib/exportReport";
import { rerunHref } from "@/lib/rerun";
import { summaryText } from "@/lib/summaryText";
import type { Run } from "@/types";

const displaySuite = (suite: string) => suite.replace(/[-_]+/g, " ").replace(/^./, (letter) => letter.toUpperCase());

function ComparePicker({ current, onPick }: { current: string; onPick: (id: string) => void }) {
  const runs = useAsync(() => api.listRuns(true), []);
  const choices = (runs.data ?? []).filter((run) => run.id !== current && run.status === "completed");
  return (
    <Card className="compare-picker mt-4 max-w-xl p-4">
      <p className="mb-2 text-sm font-semibold">{COMPARE_COPY.choose}</p>
      {runs.loading && <p className="text-xs text-faint">Loading…</p>}
      {runs.error && <p className="text-xs text-muted-foreground">{runs.error}</p>}
      {!runs.loading && !runs.error && choices.length === 0 && <p className="text-xs text-faint">No other completed reports.</p>}
      <div className="flex flex-wrap gap-2">
        {choices.map((run) => <Button key={run.id} variant="outline" size="sm" onClick={() => onPick(run.id)}>{run.request.model}{run.source === "bundled" ? " (bundled)" : ""}</Button>)}
      </div>
    </Card>
  );
}

export default function Report() {
  const { id = "" } = useParams();
  // Keying on `id` forces a full remount on every report change: without it react-router
  // reuses this instance across /reports/:id navigations, and both `loaded.data` (useAsync
  // never clears data between fetches) and LiveRunPanel's `startedAt` would keep showing
  // the previous report's content/timer until the new fetch resolves.
  return <ReportView key={id} id={id} />;
}

function ReportView({ id }: { id: string }) {
  const [params, setParams] = useSearchParams();
  const { catalog } = useCatalog();
  const loaded = useAsync(() => api.getRun(id), [id]);
  const [latest, setLatest] = useState<Run | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const run = latest ?? loaded.data;
  const terminal = useCallback((next: Run) => setLatest(next), []);

  if (loaded.loading && !run) return <div className="grid gap-4"><Skeleton className="h-16 w-2/3" /><Skeleton className="h-72" /></div>;
  if (loaded.error || !run) return <p className="text-sm text-muted-foreground">{loaded.error ?? "Report not found."}</p>;

  if (run.status === "queued" || run.status === "running") {
    const questions = run.report?.probes.length
      ?? catalog?.suites.find((suite) => suite.name === run.request.suite)?.questions
      ?? 0;
    return <div className="mx-auto max-w-3xl"><LiveRunPanel jobId={run.id} questions={questions} repeats={run.request.k} model={run.request.model} suite={run.request.suite} onTerminal={terminal} /></div>;
  }

  if (run.status === "failed" || run.status === "interrupted") {
    return <Card className="mx-auto max-w-3xl space-y-3 border-verdict-unreliable/45 p-5"><h1 className="font-display text-2xl font-bold">{REPORT_COPY.failed}</h1><p className="text-verdict-unreliable">{run.error ?? run.status}</p><p className="font-mono text-xs text-faint">{run.request.model} · {run.request.suite} · {run.request.k} repeats · {run.request.engine}</p><Button nativeButton={false} render={<Link role="link" to={rerunHref(run)} />}>{REPORT_COPY.runAgain}</Button></Card>;
  }

  if (!run.report || !run.verdict) return <p className="text-sm text-muted-foreground">This completed run has no report.</p>;

  const save = () => {
    try { downloadReport(run, "html"); } catch { toast.error(REPORT_COPY.exportFailed); }
  };
  const copy = async () => {
    try { await navigator.clipboard.writeText(summaryText(run)); toast.success(REPORT_COPY.copied); }
    catch { toast.error(REPORT_COPY.copyFailed); }
  };
  const archive = async () => {
    try { setLatest(await api.setRunArchived(run.id, !run.archived)); }
    catch { toast.error(REPORT_COPY.archiveFailed); }
  };
  const chooseComparison = (vs: string) => {
    const next = new URLSearchParams(params);
    next.set("vs", vs);
    setParams(next);
    setPickerOpen(false);
  };

  return (
    <div className="mx-auto max-w-5xl">
      <Headline run={run} suiteLabel={catalog?.suites.find((suite) => suite.name === run.request.suite)?.label ?? displaySuite(run.request.suite)} onSave={save} onCopy={() => void copy()} onCompare={() => setPickerOpen((open) => !open)} onArchive={() => void archive()} />
      {pickerOpen && <ComparePicker current={run.id} onPick={chooseComparison} />}
      {params.get("vs") && <ComparePanel run={run} vs={params.get("vs")!} />}
      <Details run={run} />
    </div>
  );
}
