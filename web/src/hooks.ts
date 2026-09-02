import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { api } from "./api";
import type { Catalog, Run } from "./types";

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

export interface RunWatchState {
  run: Run | null;
  terminal: boolean;
  error: string | null;
}

const MAX_POLL_FAILURES = 5;

/** Watch one run to its terminal state: SSE first, 2s polling as the fallback,
 *  and a full getRun once terminal (the stream carries only status/error). */
const TERMINAL = new Set<Run["status"]>(["completed", "failed", "interrupted"]);

export function useRunStatus(id: string): RunWatchState {
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let poller: ReturnType<typeof setInterval> | null = null;
    let failures = 0;
    let active = true;

    setRun(null);
    setError(null);

    const stopPolling = () => {
      if (poller) { clearInterval(poller); poller = null; }
    };

    const apply = (next: Run) => {
      if (!active) return;
      setRun(next);
      // Fall back to the current error only when this fetch didn't report one — a
      // terminal SSE message's error can otherwise be lost if the trailing getRun
      // response hasn't caught up yet.
      setError((current) => next.error ?? current);
      if (TERMINAL.has(next.status)) stopPolling();
    };

    const startPolling = () => {
      if (poller) return;
      poller = setInterval(() => {
        api.getRun(id)
          .then((next) => { failures = 0; apply(next); })
          .catch(() => { failures += 1; if (failures >= MAX_POLL_FAILURES) stopPolling(); });
      }, 2000);
    };

    const source = api.watchRun(id);
    source.onmessage = (event) => {
      const eventData = JSON.parse(event.data) as { status: Run["status"]; error: string | null };
      if (!active) return;
      setError(eventData.error);
      if (TERMINAL.has(eventData.status)) {
        source.close();
        // A transient failure here must not strand the UI mid-terminal: fall back to
        // the same polling loop onerror uses, rather than swallowing the error.
        api.getRun(id).then(apply).catch(startPolling);
      }
    };
    source.onerror = () => {
      source.close();
      startPolling();
    };

    return () => { active = false; source.close(); stopPolling(); };
  }, [id]);

  return { run, terminal: run ? TERMINAL.has(run.status) : false, error };
}
