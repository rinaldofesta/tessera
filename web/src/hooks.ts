import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Report, RunStatus } from "./types";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** Run an async fn, tracking loading/error, re-running when `deps` change. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    run()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [run, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, loading, error, reload };
}

/** Poll the API health (list runs is cheap) every `ms`. */
export function useApiHealth(ms = 5000): boolean {
  const [ok, setOk] = useState(true);
  useEffect(() => {
    let alive = true;
    const ping = () =>
      fetch("/api/orgs").then((r) => alive && setOk(r.ok)).catch(() => alive && setOk(false));
    ping();
    const t = setInterval(ping, ms);
    return () => { alive = false; clearInterval(t); };
  }, [ms]);
  return ok;
}

export interface RunStatusState {
  status: RunStatus["status"];
  report: Report | null;
  error: string | null;
  /** Epoch ms of the moment this id started being watched — for elapsed clocks. */
  startedAt: number;
}

const MAX_POLL_FAILURES = 5;

/** Watch one run to its terminal state: SSE first, 2s polling as the fallback,
 *  and a full getRun once terminal (the stream carries only status/error). */
export function useRunStatus(id: string): RunStatusState {
  const [state, setState] = useState<RunStatusState>({
    status: "running", report: null, error: null, startedAt: Date.now(),
  });

  useEffect(() => {
    let poller: ReturnType<typeof setInterval> | null = null;
    let failures = 0;
    let active = true;

    setState({ status: "running", report: null, error: null, startedAt: Date.now() });

    const stopPolling = () => {
      if (poller) { clearInterval(poller); poller = null; }
    };

    const apply = (next: RunStatus) => {
      if (!active) return;
      setState((current) => ({
        ...current,
        status: next.status,
        report: next.report ?? current.report,
        error: next.error ?? current.error,
      }));
      if (next.status !== "running") stopPolling();
    };

    const source = api.watchRun(id);
    source.onmessage = (event) => {
      const next = JSON.parse(event.data) as { status: RunStatus["status"]; error: string | null };
      if (!active) return;
      setState((current) => ({ ...current, status: next.status, error: next.error ?? current.error }));
      if (next.status !== "running") {
        source.close();
        api.getRun(id).then(apply).catch(() => {});
      }
    };
    source.onerror = () => {
      source.close();
      if (poller) return;
      poller = setInterval(() => {
        api.getRun(id)
          .then((next) => { failures = 0; apply(next); })
          .catch(() => { failures += 1; if (failures >= MAX_POLL_FAILURES) stopPolling(); });
      }, 2000);
    };

    return () => { active = false; source.close(); stopPolling(); };
  }, [id]);

  return state;
}
