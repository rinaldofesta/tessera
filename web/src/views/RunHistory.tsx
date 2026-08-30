import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api";
import { PageHeader } from "@/components/viz/PageHeader";
import { RunRow } from "@/components/viz/RunRow";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { RUN_HISTORY_COPY, STATUS_COPY } from "@/copy";
import { useAsync } from "@/hooks";

const STATUSES = ["running", "done", "error"] as const;

export default function RunHistory() {
  const runs = useAsync(() => api.listRuns(), []);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<string>("all");
  const [suite, setSuite] = useState<string>("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const rows = runs.data ?? [];
  const suites = useMemo(() => [...new Set(rows.map((r) => r.org))].sort(), [rows]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (status !== "all" && r.status !== status) return false;
      if (suite !== "all" && r.org !== suite) return false;
      if (!q) return true;
      return [r.model, r.org, r.judge, r.grader ?? ""].some((f) => f.toLowerCase().includes(q));
    });
  }, [rows, query, status, suite]);

  const toggle = (id: string, on: boolean) =>
    setSelected((current) => {
      const next = new Set(current);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  return (
    <div>
      <PageHeader
        eyebrow={RUN_HISTORY_COPY.eyebrow}
        title={RUN_HISTORY_COPY.title}
        subtitle={RUN_HISTORY_COPY.subtitle}
      />

      {runs.loading && (
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {runs.error && (
        <Alert variant="destructive">
          <AlertDescription>{runs.error}</AlertDescription>
        </Alert>
      )}

      {!runs.loading && !runs.error && rows.length === 0 && (
        <Card className="p-10 text-center text-sm text-muted-foreground">
          <p>{RUN_HISTORY_COPY.empty}</p>
          <div className="mt-4">
            <Button nativeButton={false} render={<Link role="link" to="/new" />}>
              {RUN_HISTORY_COPY.emptyCta}
            </Button>
          </div>
        </Card>
      )}

      {rows.length > 0 && (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={RUN_HISTORY_COPY.filterPlaceholder}
              className="max-w-xs"
            />
            <Select value={status} onValueChange={(value) => setStatus(value ?? "all")}>
              <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{RUN_HISTORY_COPY.statusAll}</SelectItem>
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>{STATUS_COPY[s]}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={suite} onValueChange={(value) => setSuite(value ?? "all")}>
              <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{RUN_HISTORY_COPY.suiteAll}</SelectItem>
                {suites.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="ml-auto text-xs tabular-nums text-muted-foreground">
              {RUN_HISTORY_COPY.showing(shown.length, rows.length)}
            </span>
          </div>

          <Card className="p-0">
            {shown.map((r) => (
              <RunRow key={r.id} run={r} selected={selected.has(r.id)} onSelect={toggle} />
            ))}
          </Card>
        </>
      )}
    </div>
  );
}
