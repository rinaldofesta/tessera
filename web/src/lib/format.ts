export const pct = (x: number | null | undefined) =>
  x === null || x === undefined ? "—" : `${Math.round(x * 100)}%`;

export const shortModel = (m: string) => m.split("/").pop() ?? m;

export const fmtTs = (iso: string) => iso.slice(0, 16).replace("T", " ");

/** "42s" or "3m 05s" — elapsed time since a Date.now() timestamp. */
export const elapsed = (from: number): string => {
  const seconds = Math.floor((Date.now() - from) / 1000);
  return seconds < 60
    ? `${seconds}s`
    : `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, "0")}s`;
};

/** Exact p-value, with very small values called out rather than rounded to zero. */
export const pValue = (value: number): string => (value < 0.0001 ? "< 0.0001" : value.toFixed(4));

/** Best-effort human-readable message from a thrown value of unknown shape. */
export const messageOf = (error: unknown): string =>
  error instanceof Error ? error.message : String(error);
