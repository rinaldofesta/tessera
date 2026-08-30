/** Headline number card — the graphite successor of term.tsx's Metric. */
export function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3">
      <div className="font-mono text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 font-display text-2xl font-bold tabular-nums text-foreground">
        {value}
      </div>
      {sub && <div className="mt-0.5 truncate text-[11px] text-faint">{sub}</div>}
    </div>
  );
}
