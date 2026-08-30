import React from "react";
import { Card } from "@/components/ui/card";
import { COMPARE_COPY, COMPARE_PALETTE, engineLabel } from "@/copy";
import { pct, shortModel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { EvaluationSummary } from "@/types";

const MAX = COMPARE_PALETTE.length;

interface RunPickerProps {
  evaluations: EvaluationSummary[];
  /** Ordered: index 0 is the baseline. */
  selected: string[];
  onToggle: (next: string[]) => void;
  onInspect: (id: string) => void;
  importSlot?: React.ReactNode;
}

/** The compare rail: ordered multi-select over the evaluation library.
 *  A selection keeps its palette color for as long as it stays selected. */
export function RunPicker({ evaluations, selected, onToggle, onInspect, importSlot }: RunPickerProps) {
  const toggle = (id: string) =>
    onToggle(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);

  return (
    <Card className="p-0">
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="font-mono text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
          {COMPARE_COPY.rail} ({evaluations.length})
        </span>
        <span className="text-[10px] text-faint">{COMPARE_COPY.maxSelected(MAX)}</span>
      </div>
      <div className="max-h-[480px] overflow-auto">
        {evaluations.map((item) => {
          const index = selected.indexOf(item.id);
          const isSelected = index >= 0;
          const full = !isSelected && selected.length >= MAX;
          return (
            <div
              key={item.id}
              className={cn(
                "flex items-center gap-2 border-b border-border px-3 py-2 last:border-b-0",
                isSelected && "bg-accent/40",
              )}
            >
              <input
                type="checkbox"
                className="accent-[var(--primary)]"
                checked={isSelected}
                disabled={full}
                onChange={() => toggle(item.id)}
                aria-label={`${shortModel(item.model)} · ${item.org ?? ""}`}
              />
              <span
                data-testid="color-dot"
                aria-hidden="true"
                className="size-2.5 shrink-0 rounded-full border border-border"
                style={isSelected ? { background: COMPARE_PALETTE[index] } : undefined}
              />
              <button
                type="button"
                onClick={() => toggle(item.id)}
                disabled={full}
                className="min-w-0 flex-1 text-left"
              >
                <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                  <span className="truncate">
                    {item.kind === "pinned" ? "★ " : ""}
                    {shortModel(item.model)}
                  </span>
                  {index === 0 && (
                    <span className="shrink-0 rounded-full border border-primary/55 px-1.5 text-[9px] text-primary">
                      {COMPARE_COPY.baselineTag}
                    </span>
                  )}
                </div>
                <div className="flex justify-between font-mono text-[10px] text-faint">
                  <span className="truncate">
                    {item.kind} · {engineLabel(item.engine)} · {item.epochs}×
                  </span>
                  <span className="tabular-nums">{pct(item.pass_k_rate)}</span>
                </div>
              </button>
              <button
                type="button"
                onClick={() => onInspect(item.id)}
                className="shrink-0 text-[10px] text-muted-foreground hover:text-foreground"
              >
                {COMPARE_COPY.detail}
              </button>
            </div>
          );
        })}
        {evaluations.length === 0 && (
          <p className="p-3 text-xs text-muted-foreground">{COMPARE_COPY.railEmpty}</p>
        )}
      </div>
      {importSlot && <div className="border-t border-border p-3">{importSlot}</div>}
    </Card>
  );
}
