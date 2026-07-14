import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/api";
import { RunsTable } from "@/components/RunsTable";
import { ErrLine, Metric, Panel, ViewHeader } from "@/components/term";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks";
import { pct, shortModel } from "@/lib/format";

const AXIS_TICK = { fill: "#737373", fontSize: 10, fontFamily: "inherit" } as const;

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

  return (
    <div className="space-y-4">
      <ViewHeader cmd="tessera status" desc="the reliability program at a glance — latest score, trend, recent runs" />

      {runs.loading && (
        <div className="space-y-2">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}
      {runs.error && <ErrLine msg={runs.error} />}

      {!runs.loading && !runs.error && rows.length === 0 && (
        <Panel title="run store — empty">
          <div className="py-10 text-center text-xs text-muted-foreground">
            <div>no runs recorded yet — history and trends appear after the first live eval</div>
            <div className="mt-4">
              <Button size="sm" render={<Link to="/run" />}>
                ▸ run first eval
              </Button>
            </div>
          </div>
        </Panel>
      )}

      {rows.length > 0 && (
        <>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            <Metric
              label="latest reliability"
              value={latest ? pct(latest.pass_k_rate) : "—"}
              sub={latest ? `${latest.org} · ${shortModel(latest.model)}` : "no completed runs"}
            />
            <Metric label="latest average" value={latest ? pct(latest.mean_rate) : "—"} sub="success rate" />
            <Metric label="runs total" value={String(rows.length)} />
            <Metric label="completed" value={String(done.length)} sub={errored.length ? `${errored.length} errored` : undefined} />
          </div>

          {series.length > 1 && (
            <Panel title="trend — reliability vs average (oldest → newest)">
              <ResponsiveContainer width="100%" height={190}>
                <LineChart data={series} margin={{ top: 6, right: 6, left: -24, bottom: 0 }}>
                  <CartesianGrid stroke="rgba(255,255,255,0.07)" strokeDasharray="2 4" />
                  <XAxis dataKey="n" tick={AXIS_TICK} stroke="rgba(255,255,255,0.2)" tickLine={false} />
                  <YAxis domain={[0, 100]} tick={AXIS_TICK} stroke="rgba(255,255,255,0.2)" tickLine={false} unit="%" />
                  <Tooltip
                    contentStyle={{
                      background: "#000",
                      border: "1px solid rgba(255,255,255,0.3)",
                      borderRadius: 0,
                      fontSize: 11,
                      fontFamily: "inherit",
                    }}
                    labelFormatter={(n) => `run #${n}`}
                  />
                  <Line type="stepAfter" dataKey="passk" name="reliability" stroke="#e5e5e5" strokeWidth={1.5} dot={{ r: 2, fill: "#e5e5e5", strokeWidth: 0 }} />
                  <Line type="stepAfter" dataKey="mean" name="average" stroke="#666" strokeWidth={1} strokeDasharray="4 3" dot={false} />
                </LineChart>
              </ResponsiveContainer>
              <div className="mt-1 flex gap-4 text-[10px] text-muted-foreground">
                <span>── reliability (passed every repeat — pass^k)</span>
                <span>╌╌ average success rate</span>
              </div>
            </Panel>
          )}

          <Panel
            title={rows.length > 12 ? `recent runs (12 of ${rows.length})` : `recent runs (${rows.length})`}
            right={
              <Button variant="ghost" size="xs" render={<Link to="/results" />}>
                open results →
              </Button>
            }
            bodyClassName="p-0"
          >
            <RunsTable rows={rows.slice(0, 12)} />
          </Panel>
        </>
      )}
    </div>
  );
}
