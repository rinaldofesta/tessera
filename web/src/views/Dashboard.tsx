import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { useAsync } from "../hooks";
import { Btn, Card, ErrorBox, Metric, Pill, Spinner, pct } from "../ui";

export default function Dashboard() {
  const runs = useAsync(() => api.listRuns(), []);
  const trends = useAsync(() => api.trends(), []);

  const rows = runs.data ?? [];
  const done = rows.filter((r) => r.status === "done");
  const latest = done[0];
  const series = (trends.data ?? []).map((t, i) => ({
    n: i + 1, "pass^k": Math.round(t.pass_k_rate * 100), mean: Math.round(t.mean_rate * 100),
  }));

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
      <p className="text-sm text-muted mb-4">The state of your reliability program — latest scores, the trend, and recent runs.</p>

      {runs.loading && <Spinner />}
      {runs.error && <ErrorBox msg={runs.error} />}

      {!runs.loading && rows.length === 0 && (
        <Card className="text-center py-10">
          <div className="text-muted mb-3">No runs yet.</div>
          <Link to="/run"><Btn>▶ Launch your first eval</Btn></Link>
        </Card>
      )}

      {rows.length > 0 && (
        <>
          <div className="grid grid-cols-4 gap-3 mb-4">
            <Metric label="latest pass^k" value={latest ? pct(latest.pass_k_rate) : "—"}
              tone={latest && (latest.pass_k_rate ?? 0) >= 1 ? "text-pass" : "text-fail"} />
            <Metric label="latest mean" value={latest ? pct(latest.mean_rate) : "—"} />
            <Metric label="runs (total)" value={String(rows.length)} />
            <Metric label="completed" value={String(done.length)} />
          </div>

          {series.length > 1 && (
            <Card className="mb-4">
              <div className="text-xs text-muted mb-2">pass^k trend (oldest → newest)</div>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={series} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a3343" />
                  <XAxis dataKey="n" tick={{ fill: "#9aa7b8", fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: "#9aa7b8", fontSize: 12 }} unit="%" />
                  <Tooltip contentStyle={{ background: "#161b26", border: "1px solid #2a3343", borderRadius: 8 }} />
                  <Line type="monotone" dataKey="pass^k" stroke="#22c55e" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="mean" stroke="#3b82f6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}

          <Card>
            <div className="text-xs text-muted mb-2">Recent runs</div>
            <table className="w-full text-sm">
              <thead className="text-muted text-left">
                <tr><th className="py-1">status</th><th>model</th><th>org</th><th>engine</th><th>pass^k</th><th>when</th></tr>
              </thead>
              <tbody>
                {rows.slice(0, 12).map((r) => (
                  <tr key={r.id} className="border-t border-border">
                    <td className="py-1">
                      <Pill tone={r.status === "done" ? "pass" : r.status === "error" ? "fail" : "muted"}>{r.status}</Pill>
                    </td>
                    <td>{r.model.split("/").pop()}</td>
                    <td>{r.org}</td>
                    <td>{r.judge}</td>
                    <td>{pct(r.pass_k_rate)}</td>
                    <td className="text-muted">{r.created_at.slice(0, 16).replace("T", " ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}
