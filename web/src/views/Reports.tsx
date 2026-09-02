import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/viz/PageHeader";
import { RunRow } from "@/components/viz/RunRow";
import { REPORTS_COPY } from "@/copy";
import { useAsync, useCatalog } from "@/hooks";
import { downloadReport } from "@/lib/exportReport";
import type { Run } from "@/types";

export default function Reports() {
  const [showArchived, setShowArchived] = useState(false);
  const [query, setQuery] = useState("");
  const { catalog } = useCatalog();
  const state = useAsync(() => api.listRuns(showArchived), [showArchived]);
  const rows = useMemo(() => [...(state.data ?? [])].sort((a, b) => {
    if ((a.source === "bundled") !== (b.source === "bundled")) return a.source === "bundled" ? 1 : -1;
    return Date.parse(b.created_at) - Date.parse(a.created_at);
  }), [state.data]);
  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return needle ? rows.filter((run) => run.request.model.toLowerCase().includes(needle) || run.request.suite.toLowerCase().includes(needle)) : rows;
  }, [query, rows]);

  const save = async (candidate: Run) => {
    // The list endpoint always omits `report` (routes_runs.py's list_runs uses
    // include_report=False), so a full fetch is required for every save.
    try {
      const run = await api.getRun(candidate.id);
      downloadReport(run, "html");
    } catch { toast.error(REPORTS_COPY.exportFailed); }
  };
  const archive = async (run: Run) => {
    try { await api.setRunArchived(run.id, !run.archived); state.reload(); }
    catch { toast.error(REPORTS_COPY.archiveFailed); }
  };

  return (
    <div>
      <PageHeader eyebrow={REPORTS_COPY.eyebrow} title={REPORTS_COPY.title} subtitle={REPORTS_COPY.subtitle} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={REPORTS_COPY.filterPlaceholder} aria-label={REPORTS_COPY.filterPlaceholder} className="max-w-sm" />
        <label className="flex items-center gap-2 text-xs text-muted-foreground"><input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />{REPORTS_COPY.showArchived}</label>
      </div>
      {state.loading && <div className="space-y-2"><Skeleton className="h-20" /><Skeleton className="h-20" /></div>}
      {state.error && <p className="text-sm text-muted-foreground">{state.error}</p>}
      {!state.loading && !state.error && rows.length === 0 && <Card className="p-10 text-center"><p className="text-sm text-muted-foreground">{REPORTS_COPY.empty}</p><Button className="mt-4" nativeButton={false} render={<Link role="link" to="/" />}>{REPORTS_COPY.emptyCta}</Button></Card>}
      {!state.loading && !state.error && rows.length > 0 && <Card className="p-0">{shown.length ? shown.map((run) => <RunRow key={run.id} run={run} scorerVersion={catalog?.scorers.find((scorer) => scorer.engine === run.request.engine)?.version} onSave={(item) => void save(item)} onArchive={(item) => void archive(item)} />) : <p className="p-8 text-center text-sm text-faint">No reports match that filter.</p>}</Card>}
    </div>
  );
}
