import { api } from "@/api";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { CategoryBars } from "@/components/viz/CategoryBars";
import { GapBar } from "@/components/viz/GapBar";
import { SectionLabel } from "@/components/viz/SectionLabel";
import { VerdictBadge } from "@/components/viz/VerdictBadge";
import { COMPARE_COPY, conflictLabel } from "@/copy";
import { useAsync } from "@/hooks";
import { pValue } from "@/lib/format";
import type { Run } from "@/types";

export function ComparePanel({ run, vs }: { run: Run; vs: string }) {
  const state = useAsync(
    () => Promise.all([api.getRun(vs), api.compareRuns(run.id, vs)]).then(([other, comparison]) => ({ other, comparison })),
    [run.id, vs],
  );
  if (state.loading) return <p className="mt-6 text-sm text-faint">Comparing…</p>;
  if (state.error) return <p className="mt-6 text-sm text-muted-foreground" role="status">{state.error}</p>;
  if (!state.data || !run.verdict || !state.data.other.verdict) return null;
  const { other, comparison } = state.data;
  const keys = [...new Set([
    ...(run.report?.categories.map((category) => category.key) ?? []),
    ...(other.report?.categories.map((category) => category.key) ?? []),
  ])];
  const groups = keys.map((key) => ({
    key,
    label: conflictLabel(key),
    series: [
      { id: "a", label: run.request.model, color: "var(--series-a)", value: run.report?.categories.find((category) => category.key === key)?.pass_k_rate ?? null },
      { id: "b", label: other.request.model, color: "var(--series-b)", value: other.report?.categories.find((category) => category.key === key)?.pass_k_rate ?? null },
    ],
  }));
  return (
    <Card className="mt-8 space-y-6 border-line bg-panel p-5">
      <SectionLabel>{COMPARE_COPY.title}</SectionLabel>
      <div className="grid gap-4 md:grid-cols-2">
        {[run, other].map((item) => (
          <div key={item.id} className="space-y-3 rounded-lg border border-line bg-raised p-4">
            <p className="truncate font-mono text-xs text-faint">{item.request.model}</p>
            <div className="flex flex-wrap items-center gap-2">
              <VerdictBadge verdict={item.verdict!.label} />
              <p className="font-display text-lg font-semibold">{item.verdict!.sentence}</p>
            </div>
            <GapBar passK={item.verdict!.pass_k_rate} mean={item.verdict!.mean_rate} k={item.request.k} />
          </div>
        ))}
      </div>
      <CategoryBars groups={groups} />
      <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <Badge variant="outline" className={comparison.compatible ? "border-verdict-reliable/55 text-verdict-reliable" : "border-verdict-inconsistent/55 text-verdict-inconsistent"}>
          {comparison.compatible ? COMPARE_COPY.compatible : COMPARE_COPY.incompatible}
        </Badge>
        {!comparison.compatible && comparison.unexpected_dimensions.join(", ")}
      </p>
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <span>{COMPARE_COPY.aWins} <b>{comparison.overall.a_wins}</b></span>
        <span>{COMPARE_COPY.bWins} <b>{comparison.overall.b_wins}</b></span>
        <span>{COMPARE_COPY.bothPass} <b>{comparison.overall.both_pass}</b></span>
        <span>{COMPARE_COPY.bothFail} <b>{comparison.overall.both_fail}</b></span>
        <span className="text-faint">{COMPARE_COPY.mcnemar} = {pValue(comparison.overall.p_value)}</span>
      </div>
    </Card>
  );
}
