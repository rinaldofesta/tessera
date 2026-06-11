export const pct = (x: number | null | undefined) =>
  x === null || x === undefined ? "—" : `${Math.round(x * 100)}%`;

export const shortModel = (m: string) => m.split("/").pop() ?? m;

export const fmtTs = (iso: string) => iso.slice(0, 16).replace("T", " ");
