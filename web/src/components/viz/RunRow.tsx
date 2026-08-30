import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { GAP_COPY, RUN_HISTORY_COPY, engineLabel } from "@/copy";
import { fmtTs, pct, shortModel } from "@/lib/format";
import type { RunSummary } from "@/types";
import { GapBar, gapPoints } from "./GapBar";
import { StatusBadge } from "./StatusBadge";

interface RunRowProps {
  run: RunSummary;
  selected: boolean;
  onSelect: (id: string, selected: boolean) => void;
  /** Slot for later-PR actions (Export in PR2, Archive in PR5). */
  extraActions?: React.ReactNode;
}

/** One raw run in the history: checkbox · identity · glyph · headline · time · actions.
 *  Only finished runs are selectable — they alone can cross to /compare as run:<id>. */
export function RunRow({ run, selected, onSelect, extraActions }: RunRowProps) {
  const finished = run.status === "done" && run.pass_k_rate != null && run.mean_rate != null;
  const gapPp = finished ? gapPoints(run.pass_k_rate!, run.mean_rate!) : 0;

  return (
    <div className="grid grid-cols-[auto_minmax(160px,1.2fr)_minmax(140px,1fr)_150px_auto] items-center gap-4 border-b border-border px-4 py-3 last:border-b-0 hover:bg-accent/40">
      <input
        type="checkbox"
        className="accent-[var(--primary)]"
        checked={selected}
        disabled={run.status !== "done"}
        onChange={(e) => onSelect(run.id, e.target.checked)}
        aria-label={RUN_HISTORY_COPY.selectRun(shortModel(run.model))}
      />

      <div className="min-w-0">
        <div className="truncate text-[13px] font-semibold text-foreground">
          {shortModel(run.model)}
        </div>
        <div className="truncate font-mono text-[11px] text-faint">
          {RUN_HISTORY_COPY.meta(run.org, engineLabel(run.judge), run.epochs)}
        </div>
      </div>

      {finished ? (
        <GapBar passK={run.pass_k_rate!} mean={run.mean_rate!} k={run.epochs} />
      ) : (
        <div className="flex min-w-0 items-center gap-2">
          <StatusBadge status={run.status} />
          {run.error && (
            <span className="truncate text-[11px] text-destructive" title={run.error}>
              {run.error}
            </span>
          )}
        </div>
      )}

      <div className="text-right">
        {finished ? (
          <>
            <div className="text-[15px] font-bold tabular-nums text-foreground">
              {pct(run.pass_k_rate)}
            </div>
            <div className="text-[10px] tabular-nums text-faint">
              {GAP_COPY.headline(run.epochs, pct(run.mean_rate), gapPp)}
            </div>
          </>
        ) : (
          <div className="text-[15px] font-bold text-faint">{RUN_HISTORY_COPY.noScore}</div>
        )}
        <div className="mt-0.5 font-mono text-[10px] text-faint">{fmtTs(run.created_at)}</div>
      </div>

      <div className="flex items-center gap-1.5">
        <Button variant="ghost" size="xs" nativeButton={false} render={<Link role="link" to={`/runs/${run.id}`} />}>
          {RUN_HISTORY_COPY.details}
        </Button>
        <Button variant="ghost" size="xs" nativeButton={false} render={<Link role="link" to={`/new?from=${run.id}`} />}>
          {RUN_HISTORY_COPY.rerun}
        </Button>
        {extraActions}
      </div>
    </div>
  );
}
