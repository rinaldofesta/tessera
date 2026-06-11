import { useEffect, useRef, useState } from "react";
import { api } from "@/api";
import { RunsTable } from "@/components/RunsTable";
import { Scorecard } from "@/components/Scorecard";
import { ErrLine, Panel, ViewHeader } from "@/components/term";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useAsync } from "@/hooks";
import type { Report, RunConfig } from "@/types";

const MODELS = ["anthropic/claude-sonnet-4-6", "openai/gpt-4o", "anthropic/claude-opus-4-8"];
const ENGINES = [
  { value: "llm", label: "llm — independent grader" },
  { value: "deterministic", label: "deterministic — key-free" },
];
const MAX_POLL_FAILURES = 5;

const clampEpochs = (s: string) => Math.max(1, Math.min(10, parseInt(s, 10) || 3));

export default function Run() {
  const orgs = useAsync(() => api.listOrgs().catch(() => ["toy"]), []);
  const orgList = orgs.data ?? ["toy"];

  const [model, setModel] = useState(MODELS[0]);
  const [engine, setEngine] = useState("llm");
  const [grader, setGrader] = useState(MODELS[1]);
  const [org, setOrg] = useState("toy");
  const [epochsStr, setEpochsStr] = useState("3");

  const [jobId, setJobId] = useState<string | null>(null);
  const [lines, setLines] = useState<string[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const startedAt = useRef(0);
  const lastStatus = useRef("");
  const [, tick] = useState(0);

  const history = useAsync(() => api.listRuns(), [report, error]);

  useEffect(() => {
    if (orgList.length && !orgList.includes(org)) setOrg(orgList[0]);
  }, [orgs.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const elapsed = () => Math.floor((Date.now() - startedAt.current) / 1000);
  const log = (s: string) => setLines((l) => [...l, s]);

  // elapsed ticker — independent of the watcher so it runs during the POST too
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [running]);

  function finish(id: string) {
    api
      .getRun(id)
      .then((r) => {
        if (r.status === "error") {
          setError(r.error ?? "run failed");
          log(`[+${elapsed()}s] ✗ ${r.error ?? "run failed"}`);
        } else {
          setReport(r.report);
          log(`[+${elapsed()}s] ✓ done — report ready`);
        }
      })
      .catch((e) => setError(String(e)))
      .finally(() => setRunning(false));
  }

  // Watch the job: SSE first, polling fallback if the stream drops.
  // jobId is cleared at launch, so this only ever attaches to the new job.
  useEffect(() => {
    if (!jobId || !running) return;
    let poller: ReturnType<typeof setInterval> | null = null;
    let pollFailures = 0;
    const es = new EventSource(`/api/runs/${jobId}/events`);

    const onStatus = (status: string) => {
      pollFailures = 0;
      if (status !== lastStatus.current) {
        lastStatus.current = status;
        log(`[+${elapsed()}s] status=${status}`);
      }
      if (status !== "running") {
        es.close();
        if (poller) clearInterval(poller);
        finish(jobId);
      }
    };

    es.onmessage = (ev) => onStatus(JSON.parse(ev.data).status);
    es.onerror = () => {
      // dropped stream or server ceiling — keep watching via plain polling
      es.close();
      if (poller) return;
      log(`[+${elapsed()}s] stream lost — falling back to polling`);
      poller = setInterval(() => {
        api
          .getRun(jobId)
          .then((r) => onStatus(r.status))
          .catch(() => {
            pollFailures += 1;
            if (pollFailures >= MAX_POLL_FAILURES) {
              if (poller) clearInterval(poller);
              log(`[+${elapsed()}s] ✗ lost contact with the run — is the api still up?`);
              setError("lost contact with the run — the job may still finish server-side; check history");
              setRunning(false);
            }
          });
      }, 2000);
    };

    return () => {
      es.close();
      if (poller) clearInterval(poller);
    };
  }, [jobId, running]); // eslint-disable-line react-hooks/exhaustive-deps

  function launch() {
    if (engine === "llm" && grader === model) {
      setError("grader must differ from the model under test — a model can't grade itself");
      return;
    }
    const epochs = clampEpochs(epochsStr);
    setEpochsStr(String(epochs));
    setError(null);
    setReport(null);
    setJobId(null); // detach any previous watcher before the new id arrives
    setRunning(true);
    lastStatus.current = "";
    startedAt.current = Date.now();
    const cfg: RunConfig = { model, judge: engine, org, epochs, ...(engine === "llm" ? { grader } : {}) };
    setLines([
      `$ inspect eval tessera_probes --model ${model} -T org=${org} -T judge=${engine}` +
        (engine === "llm" ? ` --model-role grader=${grader}` : "") +
        ` -T k=${epochs}`,
    ]);
    api
      .startRun(cfg)
      .then((j) => {
        setJobId(j.job_id);
        log(`[+${elapsed()}s] job ${j.job_id.slice(0, 8)} submitted`);
      })
      .catch((e) => {
        setError(String(e?.message ?? e));
        setRunning(false);
      });
  }

  function stopWatching() {
    log(`[+${elapsed()}s] watch stopped — the job keeps running server-side (see history)`);
    setRunning(false);
  }

  function reset() {
    setJobId(null);
    setReport(null);
    setError(null);
    setRunning(false);
    setLines([]);
  }

  function onModelChange(v: string) {
    setModel(v);
    if (engine === "llm" && grader === v) {
      setGrader(MODELS.find((m) => m !== v) ?? MODELS[0]);
    }
  }

  return (
    <div className="space-y-4">
      <ViewHeader
        cmd="tessera eval --live"
        desc="compile the org, run the agent over MCP tools, score pass^k — needs model keys in .env (~30–60s)"
      />

      {orgs.error && <ErrLine msg={`couldn't load orgs (a custom org may be broken): ${orgs.error}`} />}

      <div className="grid gap-4 lg:grid-cols-5">
        <Panel title="configure" className="lg:col-span-2">
          <div className="space-y-3">
            <div className="space-y-1">
              <Label className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                org / dataset
              </Label>
              <Select value={org} onValueChange={(v) => setOrg(v as string)}>
                <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {orgList.map((o) => (
                    <SelectItem key={o} value={o}>{o}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                model under test
              </Label>
              <Select value={model} onValueChange={(v) => onModelChange(v as string)}>
                <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {MODELS.map((m) => (
                    <SelectItem key={m} value={m}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                scoring engine
              </Label>
              <Select
                value={engine}
                onValueChange={(v) => setEngine(v as string)}
                items={ENGINES}
              >
                <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ENGINES.map((e) => (
                    <SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {engine === "llm" && (
              <div className="space-y-1">
                <Label className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                  independent grader
                </Label>
                <Select value={grader} onValueChange={(v) => setGrader(v as string)}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {MODELS.map((m) => (
                      <SelectItem key={m} value={m} disabled={m === model}>
                        {m}{m === model ? " (under test)" : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-1">
              <Label className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                repeats (k) — strict pass^k
              </Label>
              <Input
                type="number"
                min={1}
                max={10}
                value={epochsStr}
                onChange={(e) => setEpochsStr(e.target.value)}
                onBlur={() => setEpochsStr(String(clampEpochs(epochsStr)))}
              />
            </div>
            <div className="flex gap-2 pt-1">
              <Button onClick={launch} disabled={running} className="flex-1">
                {running ? "running…" : "▸ run eval"}
              </Button>
              {running ? (
                <Button variant="outline" onClick={stopWatching}>stop</Button>
              ) : (
                (report || error || lines.length > 0) && (
                  <Button variant="outline" onClick={reset}>reset</Button>
                )
              )}
            </div>
          </div>
        </Panel>

        <Panel title="console" className="flex flex-col lg:col-span-3" bodyClassName="min-h-0 flex-1 p-0">
          <div className="h-full min-h-[260px] overflow-auto bg-background p-3 text-xs leading-relaxed">
            {lines.length === 0 && !running ? (
              <div className="text-muted-foreground">
                — idle — configure on the left and press run
                <div className="mt-2 opacity-70">
                  the agent only sees the compiled silos through crm_lookup / docs_search /
                  docs_get_file; every probe repeats k times.
                </div>
              </div>
            ) : (
              <>
                {lines.map((l, i) => (
                  <div key={i} className={l.startsWith("$") ? "font-bold" : undefined}>{l}</div>
                ))}
                {running && (
                  <div className="cursor-blink text-muted-foreground">[+{elapsed()}s] running</div>
                )}
              </>
            )}
          </div>
        </Panel>
      </div>

      {error && (
        <div className="space-y-2">
          <ErrLine msg={error} />
          <div className="flex gap-2">
            <Button size="sm" onClick={launch}>⟳ retry</Button>
            <Button size="sm" variant="outline" onClick={reset}>reset</Button>
          </div>
        </div>
      )}

      {report && (
        <Panel title="report" right={<Button variant="ghost" size="xs" onClick={reset}>↺ new run</Button>}>
          <Scorecard key={jobId ?? "live"} report={report} />
        </Panel>
      )}

      {(history.data?.length ?? 0) > 0 && (
        <Panel
          title={
            history.data!.length > 10
              ? `history (10 of ${history.data!.length})`
              : `history (${history.data!.length})`
          }
          bodyClassName="p-0"
        >
          <RunsTable rows={history.data!.slice(0, 10)} />
        </Panel>
      )}
    </div>
  );
}
