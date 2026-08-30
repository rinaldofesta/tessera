import { pct } from "@/lib/format";

interface Series {
  id: string;
  label: string;
  color: string;
  value: number | null;
}

interface Group {
  key: string;
  label: string;
  series: Series[];
}

/** Grouped horizontal bars: one group per category, one colored bar per evaluation. */
export function CategoryBars({ groups }: { groups: Group[] }) {
  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <div
          key={group.key}
          role="img"
          aria-label={`${group.label}: ${group.series
            .map((s) => `${s.label} ${pct(s.value)}`)
            .join(", ")}`}
        >
          <div className="mb-1 text-xs text-foreground">{group.label}</div>
          <div className="space-y-1">
            {group.series.map((s) =>
              s.value == null ? (
                <div key={s.id} className="text-[10px] text-faint">
                  {s.label}: {pct(s.value)}
                </div>
              ) : (
                <div key={s.id} className="flex items-center gap-2">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--raised)]">
                    <div
                      data-bar
                      className="h-full rounded-full"
                      title={`${s.label}: ${pct(s.value)}`}
                      style={{ width: `${Math.round(s.value * 1000) / 10}%`, background: s.color }}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right text-[10px] tabular-nums text-muted-foreground">
                    {pct(s.value)}
                  </span>
                </div>
              ),
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
