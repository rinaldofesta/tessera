import { SectionLabel } from "@/components/viz/SectionLabel";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { COMPARE_COPY as C } from "@/copy";
import type { Diagnostic, EvaluationSummary } from "@/types";

interface DiagnosticsState {
  loading: boolean;
  error: string | null;
  data: Diagnostic[] | null;
}

/** Receipt fingerprints + failure signatures for one evaluation — the integrity panel
 *  relocated from the retired Results view. */
export function EvaluationDetail({ item, diagnostics }: { item: EvaluationSummary; diagnostics: DiagnosticsState }) {
  const receipt = item.receipt;
  return (
    <Card className="space-y-4 p-4">
      <div>
        <SectionLabel>{C.detail}</SectionLabel>
        <dl className="grid gap-x-4 gap-y-2 text-xs sm:grid-cols-2">
          <div>
            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">{C.protocolFingerprint}</dt>
            <dd className="truncate font-mono" title={receipt.protocol_hash}>{receipt.protocol_hash.slice(0, 16)}…</dd>
          </div>
          <div>
            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">{C.executionFingerprint}</dt>
            <dd className="truncate font-mono" title={receipt.execution_hash}>{receipt.execution_hash.slice(0, 16)}…</dd>
          </div>
          <div>
            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">{C.effectiveModel}</dt>
            <dd>{receipt.runtime.effective_models.join(", ") || C.notReported}</dd>
          </div>
          <div>
            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">{C.billedCost}</dt>
            <dd className="tabular-nums">
              {receipt.usage.billed_cost == null ? C.notReported : `$${receipt.usage.billed_cost.toFixed(4)}`}
              {receipt.timing.duration_seconds != null && ` · ${C.duration(receipt.timing.duration_seconds.toFixed(1))}`}
            </dd>
          </div>
        </dl>
      </div>
      <div>
        <SectionLabel>{C.signatures}</SectionLabel>
        {diagnostics.loading && <Skeleton className="h-10 w-full" />}
        {diagnostics.error && (
          <Alert variant="destructive"><AlertDescription>{diagnostics.error}</AlertDescription></Alert>
        )}
        {!diagnostics.loading && !diagnostics.error && (
          diagnostics.data?.length ? (
            <div className="grid gap-1 text-xs sm:grid-cols-2">
              {diagnostics.data.map((entry) => (
                <div key={`${entry.kind}:${entry.signature}`} className="flex justify-between gap-3 border-b border-border py-1 last:border-b-0">
                  <span className="truncate">{entry.kind.replace(/_/g, " ")} · {entry.signature}</span>
                  <span className="tabular-nums text-muted-foreground">×{entry.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">{C.noSignatures}</p>
          )
        )}
      </div>
    </Card>
  );
}
