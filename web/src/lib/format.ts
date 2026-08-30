export const pct = (x: number | null | undefined) =>
  x === null || x === undefined ? "—" : `${Math.round(x * 100)}%`;

export const shortModel = (m: string) => m.split("/").pop() ?? m;

export const fmtTs = (iso: string) => iso.slice(0, 16).replace("T", " ");

/** Exact p-value, with very small values called out rather than rounded to zero. */
export const pValue = (value: number): string => (value < 0.0001 ? "< 0.0001" : value.toFixed(4));

/** Best-effort human-readable message from a thrown value of unknown shape. */
export const messageOf = (error: unknown): string =>
  error instanceof Error ? error.message : String(error);
