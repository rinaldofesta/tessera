import { ExternalLink } from "lucide-react";
import { api } from "@/api";
import { GapBar, gapPoints } from "@/components/viz/GapBar";
import { PageHeader } from "@/components/viz/PageHeader";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { conflictLabel, GAP_COPY, LEADERBOARD_COPY } from "@/copy";
import { useAsync } from "@/hooks";
import { pct, shortModel } from "@/lib/format";

const LEADERBOARD_URL =
  "https://github.com/rinaldofesta/tessera/blob/main/docs/leaderboard.md";

export default function Leaderboard() {
  const leaderboard = useAsync(() => api.leaderboard(), []);
  const manifest = leaderboard.data;
  // Exhibitions render once the manifest carries content for them.
  const rows = [...(manifest?.rows ?? [])].sort(
    (a, b) => b.pass_k_rate - a.pass_k_rate || b.mean_rate - a.mean_rate,
  );

  return (
    <div>
      <PageHeader eyebrow={LEADERBOARD_COPY.eyebrow} title={manifest?.title ?? LEADERBOARD_COPY.title} subtitle={LEADERBOARD_COPY.subtitle} />

      {leaderboard.loading && <div className="space-y-2"><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /></div>}
      {leaderboard.error && <Alert variant="destructive"><AlertDescription>{LEADERBOARD_COPY.loadFailed(leaderboard.error)}</AlertDescription></Alert>}
      {!leaderboard.loading && !leaderboard.error && rows.length === 0 && <Card className="p-10 text-center text-sm text-muted-foreground">{LEADERBOARD_COPY.empty}</Card>}
      {!leaderboard.loading && !leaderboard.error && rows.length > 0 && (
        <Card className="p-0">
          {rows.map((row, index) => {
            const gap = gapPoints(row.pass_k_rate, row.mean_rate);
            return (
              <div key={`${row.model}-${row.date ?? index}`} className="grid grid-cols-[auto_minmax(160px,1fr)_minmax(140px,1fr)_auto] items-center gap-4 border-b border-border px-4 py-3 last:border-b-0">
                <span className="font-mono text-xs text-faint">#{index + 1}</span>
                <div className="min-w-0">
                  <div className="truncate text-[13px] font-semibold text-foreground">{shortModel(row.model)}</div>
                  <div className="flex flex-wrap gap-x-2 font-mono text-[11px] text-faint">
                    <span>{LEADERBOARD_COPY.protocol(row.org ?? "?", row.k, row.scorer_version ?? "?")}</span>
                    {row.date && <span>{row.date}</span>}
                    {row.scaffold && row.scaffold !== "baseline" && <span>{LEADERBOARD_COPY.scaffoldTag(row.scaffold)}</span>}
                    {row.seed ? <span>{LEADERBOARD_COPY.seedTag(row.seed)}</span> : null}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {Object.entries(row.categories).map(([key, value]) => <Badge key={key} variant="outline">{conflictLabel(key)} {pct(value)}</Badge>)}
                  </div>
                </div>
                <GapBar passK={row.pass_k_rate} mean={row.mean_rate} k={row.k} />
                <div className="text-right">
                  <div className="text-[15px] font-bold tabular-nums text-foreground">{pct(row.pass_k_rate)}</div>
                  <div className="text-[10px] tabular-nums text-faint">{GAP_COPY.headline(row.k, pct(row.mean_rate), gap)}</div>
                </div>
              </div>
            );
          })}
        </Card>
      )}
      <a href={LEADERBOARD_URL} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary underline-offset-4 hover:underline">
        {LEADERBOARD_COPY.canonical}<ExternalLink aria-hidden="true" className="size-3.5" />
      </a>
    </div>
  );
}
