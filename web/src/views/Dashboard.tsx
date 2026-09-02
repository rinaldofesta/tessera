import { Link } from "react-router-dom";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/api";
import { PageHeader } from "@/components/viz/PageHeader";
import { RunRow } from "@/components/viz/RunRow";
import { StatTile } from "@/components/viz/StatTile";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DASHBOARD_COPY } from "@/copy";
import { useAsync } from "@/hooks";
import { pct, shortModel } from "@/lib/format";

const AXIS_TICK = { fill: "var(--faint)", fontSize: 10, fontFamily: "inherit" } as const;
const TOOLTIP_STYLE = {
  background: "var(--popover)", border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", fontSize: 11, fontFamily: "inherit",
} as const;

export default function Dashboard() {
  const runs = useAsync(() => api.listRuns(), []);
  const trends = useAsync(() => api.trends(), []);

  const rows = runs.data ?? [];
  const done = rows.filter((r) => r.status === "done");
  const errored = rows.filter((r) => r.status === "error");
  const latest = done[0];
  const series = (trends.data ?? []).map((t, i) => ({
    n: i + 1,
    passk: Math.round(t.pass_k_rate * 100),
    mean: Math.round(t.mean_rate * 100),
  }));
  const loading = runs.loading || trends.loading;
  const error = runs.error ?? trends.error;
  const recent = rows.slice(0, 12);

  return (
    <div>
      <PageHeader eyebrow={DASHBOARD_COPY.eyebrow} title={DASHBOARD_COPY.title} subtitle={DASHBOARD_COPY.subtitle} />

      {loading && (
        <div className="space-y-2">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {!loading && !error && rows.length === 0 && (
        <Card className="p-10 text-center text-sm text-muted-foreground">
          <div>
            <p>{DASHBOARD_COPY.emptyTitle}</p>
            <p className="mt-1">{DASHBOARD_COPY.emptyBody}</p>
            <div className="mt-4">
              <Button nativeButton={false} render={<Link role="link" to="/new" />}>
                {DASHBOARD_COPY.emptyCta}
              </Button>
            </div>
          </div>
        </Card>
      )}

      {!loading && !error && rows.length > 0 && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            <StatTile
              label={DASHBOARD_COPY.latestReliability}
              value={latest ? pct(latest.pass_k_rate) : "—"}
              sub={latest ? `${latest.org} · ${shortModel(latest.model)}` : DASHBOARD_COPY.noCompleted}
            />
            <StatTile label={DASHBOARD_COPY.latestAverage} value={latest ? pct(latest.mean_rate) : "—"} sub={DASHBOARD_COPY.averageSubtitle} />
            <StatTile label={DASHBOARD_COPY.runsTotal} value={String(rows.length)} />
            <StatTile label={DASHBOARD_COPY.completed} value={String(done.length)} sub={errored.length ? DASHBOARD_COPY.errored(errored.length) : undefined} />
          </div>

          {series.length > 1 && (
            <Card className="p-4">
              <div>
                <h2 className="font-display text-lg font-semibold text-foreground">{DASHBOARD_COPY.trendTitle}</h2>
                <p className="text-sm text-muted-foreground">{DASHBOARD_COPY.trendSubtitle}</p>
              </div>
              <ResponsiveContainer width="100%" height={190}>
                <ComposedChart data={series} margin={{ top: 6, right: 6, left: -24, bottom: 0 }}>
                  <CartesianGrid stroke="var(--line)" strokeDasharray="2 4" />
                  <XAxis dataKey="n" tick={AXIS_TICK} stroke="var(--line)" tickLine={false} />
                  <YAxis domain={[0, 100]} tick={AXIS_TICK} stroke="var(--line)" tickLine={false} unit="%" />
                  <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(n) => `run #${n}`} />
                  <Area type="stepAfter" dataKey={(d) => [d.passk, d.mean]} stroke="none" fill="var(--verdict-inconsistent)" fillOpacity={0.18} isAnimationActive={false} />
                  <Line type="stepAfter" dataKey="passk" name={DASHBOARD_COPY.legendReliability} stroke="var(--chart-1)" strokeWidth={1.5} dot={{ r: 2, fill: "var(--chart-1)", strokeWidth: 0 }} />
                  <Line type="stepAfter" dataKey="mean" name={DASHBOARD_COPY.legendAverage} stroke="var(--chart-5)" strokeWidth={1} strokeDasharray="4 3" dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
              <div className="mt-1 flex gap-4 text-[10px] text-muted-foreground">
                <span>{DASHBOARD_COPY.legendReliability}</span>
                <span>{DASHBOARD_COPY.legendAverage}</span>
              </div>
            </Card>
          )}

          <section>
            <div className="mb-2 flex items-center justify-between gap-4">
              <h2 className="font-display text-lg font-semibold text-foreground">{DASHBOARD_COPY.recentTitle(recent.length, rows.length)}</h2>
              <Button variant="ghost" size="xs" nativeButton={false} render={<Link role="link" to="/runs" />}>
                {DASHBOARD_COPY.openRuns}
              </Button>
            </div>
            <Card className="p-0">
              {recent.map((run) => <RunRow key={run.id} run={run} />)}
            </Card>
          </section>
        </div>
      )}
    </div>
  );
}
