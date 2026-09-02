import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { REPORTS_COPY } from "@/copy";
import { fmtTs, pct, shortModel } from "@/lib/format";
import { rerunHref } from "@/lib/rerun";
import type { Run } from "@/types";
import { GapBar } from "./GapBar";
import { StatusBadge } from "./StatusBadge";
import { VerdictBadge } from "./VerdictBadge";

interface RunRowProps {
  run: Run;
  scorerVersion?: string;
  onSave?: (run: Run) => void;
  onArchive?: (run: Run) => void;
}

export function RunRow({ run, scorerVersion, onSave, onArchive }: RunRowProps) {
  const complete = run.status === "completed" && run.verdict;
  const scorer = run.receipt?.protocol.scorer_version ?? run.report?.header.scorer_version ?? scorerVersion ?? run.request.engine;
  const when = run.source === "bundled" ? "bundled example" : fmtTs(run.created_at);
  return (
    <div className="grid gap-4 border-b border-line px-4 py-4 last:border-b-0 hover:bg-raised md:grid-cols-[minmax(180px,1.25fr)_minmax(130px,.8fr)_130px_auto] md:items-center">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-semibold">{shortModel(run.request.model)}</span>
          {run.archived && <Badge variant="outline" className="text-faint">{REPORTS_COPY.archived}</Badge>}
        </div>
        <p className="truncate font-mono text-[11px] text-faint">{run.request.suite} · k={run.request.k} · {scorer} · {when}</p>
      </div>
      <div>{complete ? <GapBar passK={run.verdict!.pass_k_rate} mean={run.verdict!.mean_rate} k={run.request.k} /> : <StatusBadge status={run.status} />}</div>
      <div className="flex items-center gap-2 md:block md:text-right">
        {complete ? <><VerdictBadge verdict={run.verdict!.label} /><p className="mt-1 font-display text-lg font-bold tabular-nums">{pct(run.verdict!.pass_k_rate)}</p></> : run.error && <p className="truncate text-xs text-verdict-unreliable" title={run.error}>{run.error}</p>}
      </div>
      <div className="flex flex-wrap gap-1.5 md:justify-end">
        <Button variant="ghost" size="xs" nativeButton={false} render={<Link role="link" to={`/reports/${run.id}`} />}>{REPORTS_COPY.open}</Button>
        <Button variant="ghost" size="xs" nativeButton={false} render={<Link role="link" to={rerunHref(run)} />}>{REPORTS_COPY.runAgain}</Button>
        {complete && <Button variant="ghost" size="xs" onClick={() => onSave?.(run)}>{REPORTS_COPY.saveHtml}</Button>}
        {run.source !== "bundled" && run.status !== "running" && <Button variant="ghost" size="xs" onClick={() => onArchive?.(run)}>{run.archived ? REPORTS_COPY.restore : REPORTS_COPY.archive}</Button>}
      </div>
    </div>
  );
}
