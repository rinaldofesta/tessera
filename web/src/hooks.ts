import { useCallback, useEffect, useState } from "react";

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
