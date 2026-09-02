import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { api } from "./api";
import { toLegacyStatus } from "./lib/runStatus";
import type { Catalog, Report, Run, RunStatus } from "./types";

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

interface CatalogState {
  catalog: Catalog | null;
  error: string | null;
}

let catalogState: CatalogState = { catalog: null, error: null };
let catalogRequest: Promise<void> | null = null;
// Bumped each time a *new* fetch actually starts, so an older request that resolves
// after a newer one can't overwrite catalogState with stale data (a forced reload
// racing an in-flight non-forced one would otherwise let whichever settles last win,
// regardless of which was issued more recently).
let catalogGeneration = 0;
const catalogListeners = new Set<() => void>();

function emitCatalog() {
  catalogListeners.forEach((listener) => listener());
}

function loadCatalog(force = false): Promise<void> {
  // `force` must win over "a fetch is already in flight" — otherwise a forced
  // reload (e.g. right after saving a provider key) silently rides an older,
  // pre-save request instead of refetching.
  if (catalogRequest && !force) return catalogRequest;
  if (catalogState.catalog && !force) return Promise.resolve();
  const generation = ++catalogGeneration;
  const request: Promise<void> = api.catalog()
    .then((catalog) => {
      if (generation !== catalogGeneration) return;
      catalogState = { catalog, error: null };
      emitCatalog();
    })
    .catch((error) => {
      if (generation !== catalogGeneration) return;
      catalogState = {
        ...catalogState,
        error: error instanceof Error ? error.message : String(error),
      };
      emitCatalog();
    })
    .finally(() => { if (catalogRequest === request) catalogRequest = null; });
  catalogRequest = request;
  return request;
}

function subscribeCatalog(listener: () => void) {
  catalogListeners.add(listener);
  return () => {
    catalogListeners.delete(listener);
    if (catalogListeners.size === 0) {
      catalogState = { catalog: null, error: null };
      catalogRequest = null;
    }
  };
}

export function useCatalog(): CatalogState & { reload: () => void } {
  const state = useSyncExternalStore(subscribeCatalog, () => catalogState, () => catalogState);
  useEffect(() => {
    void loadCatalog();
  }, []);
  const reload = useCallback(() => { void loadCatalog(true); }, []);
  return { ...state, reload };
}

/** Poll the shared catalog resource every 30 seconds; views reuse the same response. */
export function useApiHealth(ms = 30_000): boolean {
  const { error, reload } = useCatalog();
  useEffect(() => {
    const timer = setInterval(reload, ms);
    return () => clearInterval(timer);
  }, [ms, reload]);
  return error === null;
}

export interface RunStatusState {
  status: RunStatus["status"];
  report: Report | null;
  verdict: Run["verdict"];
  error: string | null;
  /** Epoch ms of the moment this id started being watched — for elapsed clocks. */
  startedAt: number;
}

const MAX_POLL_FAILURES = 5;

/** Watch one run to its terminal state: SSE first, 2s polling as the fallback,
 *  and a full getRun once terminal (the stream carries only status/error). */
export function useRunStatus(id: string): RunStatusState {
  const [state, setState] = useState<RunStatusState>({
    status: "running", report: null, verdict: null, error: null, startedAt: Date.now(),
  });

  useEffect(() => {
    let poller: ReturnType<typeof setInterval> | null = null;
    let failures = 0;
    let active = true;

    setState({ status: "running", report: null, verdict: null, error: null, startedAt: Date.now() });

    const stopPolling = () => {
      if (poller) { clearInterval(poller); poller = null; }
    };

    const apply = (next: RunStatus) => {
      if (!active) return;
      setState((current) => ({
        ...current,
        status: next.status,
        report: next.report ?? current.report,
        verdict: next.verdict ?? current.verdict,
        error: next.error ?? current.error,
      }));
      if (next.status !== "running") stopPolling();
    };

    const source = api.watchRun(id);
    source.onmessage = (event) => {
      const eventData = JSON.parse(event.data) as { status: Run["status"]; error: string | null };
      const next = { ...eventData, status: toLegacyStatus(eventData.status) };
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
