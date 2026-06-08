import { useState } from "react";
import { api } from "../api";
import { Scorecard } from "../components/Scorecard";
import { useAsync } from "../hooks";
import type { LogMeta, Report } from "../types";
import { Btn, Card, ErrorBox, Spinner, inputCls, pct } from "../ui";

function label(m: LogMeta): string {
  const model = m.model.split("/").pop();
  const grader = m.grader ? ` / ${m.grader.split("/").pop()}` : "";
  const star = m.source === "examples" ? "⭐ " : "";
  return `${star}${model}${grader} · ${m.engine}${m.org ? ` · ${m.org}` : ""} · ${m.created.slice(0, 10)}`;
}

function DiffTable({ a, b }: { a: Report; b: Report }) {
  const order = ["none", "resolvable", "unresolvable", "void"];
  const da = Object.fromEntries(a.categories.map((c) => [c.key, c.pass_k_rate]));
  const db = Object.fromEntries(b.categories.map((c) => [c.key, c.pass_k_rate]));
  const rows = order.filter((k) => k in da || k in db).map((k) => ({ k, a: da[k], b: db[k] }));
  rows.push({ k: "OVERALL", a: a.overall.pass_k_rate, b: b.overall.pass_k_rate });
  return (
    <Card className="mb-4">
      <div className="text-xs text-muted mb-2">Side-by-side — pass^k by conflict type</div>
      <table className="w-full text-sm">
        <thead className="text-muted text-left"><tr><th className="py-1">conflict</th><th>Run A</th><th>Run B</th><th>Δ (B−A)</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.k} className="border-t border-border">
              <td className="py-1">{r.k}</td><td>{pct(r.a)}</td><td>{pct(r.b)}</td>
              <td>{r.a != null && r.b != null ? `${Math.round((r.b - r.a) * 100) >= 0 ? "+" : ""}${Math.round((r.b - r.a) * 100)} pts` : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

export default function Results() {
  const logs = useAsync(() => api.listLogs(), []);
  const [compare, setCompare] = useState(false);
  const [a, setA] = useState<string>("");
  const [b, setB] = useState<string>("");

  const list = logs.data ?? [];
  const idA = a || list.find((l) => l.id.includes("first-contact"))?.id || list[0]?.id || "";
  const idB = b || list.find((l) => l.id.includes("gpt-4o"))?.id || list[1]?.id || "";
  const repA = useAsync(() => (idA ? api.getReport(idA) : Promise.resolve(null as unknown as Report)), [idA]);
  const repB = useAsync(() => (compare && idB ? api.getReport(idB) : Promise.resolve(null as unknown as Report)), [idB, compare]);

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-2xl font-bold">Results</h1>
        <Btn variant="ghost" onClick={() => setCompare((c) => !c)}>{compare ? "Single" : "Compare two"}</Btn>
      </div>
      <p className="text-sm text-muted mb-4">Read a run's scorecard down to the failed transcripts. pass^k is strict — right every repeat.</p>

      {logs.loading && <Spinner />}
      {logs.error && <ErrorBox msg={logs.error} />}

      <div className={`grid gap-3 mb-4 ${compare ? "grid-cols-2" : "grid-cols-1"}`}>
        <select className={inputCls} value={idA} onChange={(e) => setA(e.target.value)}>
          {list.map((l) => <option key={l.id} value={l.id}>{label(l)}</option>)}
        </select>
        {compare && (
          <select className={inputCls} value={idB} onChange={(e) => setB(e.target.value)}>
            {list.map((l) => <option key={l.id} value={l.id}>{label(l)}</option>)}
          </select>
        )}
      </div>

      {compare && repA.data && repB.data && <DiffTable a={repA.data} b={repB.data} />}

      <div className={`grid gap-6 ${compare ? "grid-cols-2" : "grid-cols-1"}`}>
        <div>{repA.loading ? <Spinner /> : repA.error ? <ErrorBox msg={repA.error} /> : repA.data && <Scorecard report={repA.data} />}</div>
        {compare && <div>{repB.loading ? <Spinner /> : repB.error ? <ErrorBox msg={repB.error} /> : repB.data && <Scorecard report={repB.data} />}</div>}
      </div>
    </div>
  );
}
