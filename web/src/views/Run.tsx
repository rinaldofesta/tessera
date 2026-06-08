import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Scorecard } from "../components/Scorecard";
import { useAsync } from "../hooks";
import type { Report } from "../types";
import { Btn, Card, ErrorBox, Field, Pill, Spinner, inputCls, pct } from "../ui";

const MODELS = ["anthropic/claude-sonnet-4-6", "openai/gpt-4o", "anthropic/claude-opus-4-8"];

export default function Run() {
  const orgs = useAsync(() => api.listOrgs().catch(() => ["toy"]), []);
  const orgList = orgs.data ?? ["toy"];

  const [model, setModel] = useState(MODELS[0]);
  const [engine, setEngine] = useState("llm");
  const [grader, setGrader] = useState(MODELS[1]);
  const [org, setOrg] = useState("toy");
  const [epochs, setEpochs] = useState(3);

  const [jobId, setJobId] = useState<string | null>(null);
  const [cfg, setCfg] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState<string>("");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const startedAt = useRef<number>(0);
  const [, force] = useState(0);

  useEffect(() => { if (orgList.length && !orgList.includes(org)) setOrg(orgList[0]); }, [orgs.data]); // eslint-disable-line

  // SSE: watch a running job until terminal, then fetch the final report.
  useEffect(() => {
    if (!jobId || report || error) return;
    const es = new EventSource(`/api/runs/${jobId}/events`);
    es.onmessage = (ev) => {
      const d = JSON.parse(ev.data);
      setStatus(d.status);
      if (d.status !== "running") {
        es.close();
        api.getRun(jobId).then((r) => {
          if (r.status === "error") setError(r.error ?? "run failed");
          else setReport(r.report);
        }).catch((e) => setError(String(e)));
      }
    };
    es.onerror = () => { es.close(); };
    const tick = setInterval(() => force((n) => n + 1), 1000); // elapsed timer
    return () => { es.close(); clearInterval(tick); };
  }, [jobId, report, error]);

  function launch() {
    setError(null); setReport(null); setStatus("running");
    const payload: Record<string, unknown> = { model, judge: engine, org, epochs };
    if (engine === "llm") payload.grader = grader;
    if (engine === "llm" && grader === model) { setError("Grader must differ from the model under test."); setStatus(""); return; }
    setCfg(payload);
    startedAt.current = Date.now();
    api.startRun(payload as any).then((j) => setJobId(j.job_id)).catch((e) => { setError(String(e)); setStatus(""); });
  }
  function reset() { setJobId(null); setReport(null); setError(null); setStatus(""); setCfg(null); }

  const running = jobId && status === "running" && !report && !error;
  const elapsed = running ? Math.floor((Date.now() - startedAt.current) / 1000) : 0;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Run a live eval</h1>
      <p className="text-sm text-muted mb-4">Compiles the org, runs the agent over MCP tools, scores pass^k. Needs model keys in <code>.env</code>. ~30–60s.</p>

      {orgs.error && <div className="mb-3"><ErrorBox msg={`Couldn't load orgs (a custom org may be broken): ${orgs.error}`} /></div>}

      <Card className="mb-4">
        <div className="grid grid-cols-2 gap-x-4">
          <Field label="Org (dataset to evaluate)">
            <select className={inputCls} value={org} onChange={(e) => setOrg(e.target.value)}>
              {orgList.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </Field>
          <Field label="Model under test">
            <select className={inputCls} value={model} onChange={(e) => setModel(e.target.value)}>
              {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
          <Field label="Scoring engine">
            <select className={inputCls} value={engine} onChange={(e) => setEngine(e.target.value)}>
              <option value="llm">llm (independent grader)</option>
              <option value="deterministic">deterministic (free, no grader)</option>
            </select>
          </Field>
          {engine === "llm" ? (
            <Field label="Independent grader">
              <select className={inputCls} value={grader} onChange={(e) => setGrader(e.target.value)}>
                {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </Field>
          ) : <div />}
          <Field label="Repeats (k)">
            <input type="number" min={1} max={10} className={inputCls} value={epochs}
              onChange={(e) => setEpochs(Math.max(1, Math.min(10, +e.target.value || 1)))} />
          </Field>
        </div>
        <Btn onClick={launch} disabled={!!running}>▶ Run eval</Btn>
      </Card>

      {cfg && (
        <div className="text-xs text-muted mb-3">
          <b>Config</b> — org <code>{String(cfg.org)}</code> · model <code>{String(cfg.model)}</code> · engine {String(cfg.judge)}
          {cfg.grader ? <> · grader <code>{String(cfg.grader)}</code></> : null} · k {String(cfg.epochs)}
        </div>
      )}
      {running && <Card className="mb-4"><Spinner /> <span className="ml-2">Running… {elapsed}s</span></Card>}
      {error && (
        <div className="mb-4 space-y-2">
          <ErrorBox msg={`Run failed: ${error}`} />
          <div className="flex gap-2"><Btn onClick={launch}>⟳ Retry</Btn><Btn variant="ghost" onClick={reset}>↺ Reset</Btn></div>
        </div>
      )}
      {report && (
        <Card className="mb-6">
          <div className="flex justify-between items-center mb-3">
            <Pill tone="pass">✅ Done</Pill>
            <Btn variant="ghost" onClick={reset}>↺ New run</Btn>
          </div>
          <Scorecard report={report} />
        </Card>
      )}

      <History />
    </div>
  );
}

function History() {
  const runs = useAsync(() => api.listRuns(), []);
  const rows = runs.data ?? [];
  if (!rows.length) return null;
  return (
    <Card>
      <div className="text-xs text-muted mb-2">Run history</div>
      <table className="w-full text-sm">
        <tbody>
          {rows.slice(0, 10).map((r) => (
            <tr key={r.id} className="border-t border-border">
              <td className="py-1"><Pill tone={r.status === "done" ? "pass" : r.status === "error" ? "fail" : "muted"}>{r.status}</Pill></td>
              <td>{r.model.split("/").pop()}</td><td>{r.org}</td><td>{r.judge}</td>
              <td>{pct(r.pass_k_rate)}</td>
              <td className="text-muted">{r.created_at.slice(0, 16).replace("T", " ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
