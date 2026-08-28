import { RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MODEL_COPY, PROVIDER_LABELS, WIZARD_COPY } from "@/copy";
import { cn } from "@/lib/utils";
import type { EvalSetupModel, SourceStatus } from "@/types";

const SELECTABLE = new Set<EvalSetupModel["readiness"]>(["ready", "unverified"]);
export const CUSTOM = "__custom__";

interface ModelStepProps {
  models: EvalSetupModel[];
  sources: SourceStatus[];
  value?: string;
  customId: string;
  onChange: (id: string) => void;
  onCustomId: (v: string) => void;
  onRescan: () => void;
  rescanning: boolean;
  onBack: () => void;
  onContinue: () => void;
}

export function ModelStep({
  models,
  sources,
  value,
  customId,
  onChange,
  onCustomId,
  onRescan,
  rescanning,
  onBack,
  onContinue,
}: ModelStepProps) {
  const usable = models.filter((model) => SELECTABLE.has(model.readiness));
  const hidden = models.length - usable.length;
  const groups = [
    {
      curated: true,
      label: MODEL_COPY.curatedGroup,
      items: usable.filter((model) => model.curated),
    },
    {
      curated: false,
      label: MODEL_COPY.discoveredGroup,
      items: usable.filter((model) => !model.curated),
    },
  ].filter((group) => group.items.length > 0);

  const ready = value === CUSTOM ? customId.trim().length > 0 : Boolean(value);

  return (
    <div>
      <h2 className="font-display text-2xl font-bold tracking-tight">{WIZARD_COPY.q2}</h2>
      <p className="mt-1 mb-4 text-sm text-[var(--muted-foreground)]">{WIZARD_COPY.q2sub}</p>

      {hidden > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-[color-mix(in_oklab,var(--verdict-inconsistent)_30%,transparent)] bg-[color-mix(in_oklab,var(--verdict-inconsistent)_9%,var(--card))] px-3.5 py-2.5 text-[12.5px]">
          <Badge
            variant="outline"
            className="border-[var(--verdict-inconsistent)]/55 text-[var(--verdict-inconsistent)]"
          >
            {MODEL_COPY.hiddenCount(hidden)}
          </Badge>
          <span>{MODEL_COPY.hiddenWhy}</span>
          <Link to="/providers" className="text-[var(--primary)] hover:underline">
            {MODEL_COPY.addProvider}
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={onRescan}
            disabled={rescanning}
            className="ml-auto gap-1.5"
          >
            <RefreshCw
              className={cn(
                "size-3.5",
                rescanning && "animate-spin motion-reduce:animate-none",
              )}
            />
            {rescanning ? MODEL_COPY.rescanning : MODEL_COPY.rescan}
          </Button>
        </div>
      )}

      <div
        role="radiogroup"
        aria-label={WIZARD_COPY.q2}
        className="overflow-hidden rounded-lg border border-[var(--border)]"
      >
        {groups.map((group) => (
          <div key={String(group.curated)}>
            <p className="border-b border-[var(--border)] bg-[#101216] px-3.5 pt-2.5 pb-1.5 font-mono text-[10.5px] uppercase tracking-[0.12em] text-[var(--faint)]">
              {group.label}
            </p>
            {group.items.map((model) => {
              const selected = model.id === value;

              return (
                <button
                  key={model.id}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => onChange(model.id)}
                  className={cn(
                    "flex w-full items-center gap-3 border-b border-[var(--border)] px-3.5 py-2.5 text-left outline-none last:border-b-0",
                    "focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--ring)]",
                    selected
                      ? "bg-[color-mix(in_oklab,var(--primary)_12%,var(--card))] shadow-[inset_2px_0_0_var(--primary)]"
                      : "bg-[var(--card)] hover:bg-[var(--raised)]",
                  )}
                >
                  <span className="min-w-0 flex-1 truncate font-mono text-[12.5px]">
                    {model.label}
                  </span>
                  <span className="hidden font-mono text-[10.5px] text-[var(--faint)] sm:inline">
                    {PROVIDER_LABELS[model.provider] ?? model.provider}
                  </span>
                  {model.readiness === "unverified" ? (
                    <Badge
                      variant="outline"
                      className="border-[var(--verdict-inconsistent)]/55 text-[var(--verdict-inconsistent)]"
                    >
                      {MODEL_COPY.unchecked}
                    </Badge>
                  ) : (
                    <Badge
                      variant="outline"
                      className="border-[var(--verdict-reliable)]/55 text-[var(--verdict-reliable)]"
                    >
                      {MODEL_COPY.ready}
                    </Badge>
                  )}
                </button>
              );
            })}
          </div>
        ))}

        <button
          type="button"
          role="radio"
          aria-checked={value === CUSTOM}
          onClick={() => onChange(CUSTOM)}
          className={cn(
            "flex w-full items-center gap-3 border-t border-[var(--border)] px-3.5 py-2.5 text-left outline-none",
            "focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--ring)]",
            value === CUSTOM
              ? "bg-[color-mix(in_oklab,var(--primary)_12%,var(--card))] shadow-[inset_2px_0_0_var(--primary)]"
              : "bg-[var(--card)] hover:bg-[var(--raised)]",
          )}
        >
          <span className="flex-1 text-[12.5px] text-[var(--muted-foreground)]">
            {MODEL_COPY.customRow}
          </span>
        </button>
      </div>

      {value === CUSTOM && (
        <div className="mt-3">
          <Input
            autoFocus
            value={customId}
            onChange={(event) => onCustomId(event.target.value)}
            placeholder={MODEL_COPY.customPlaceholder}
            className="font-mono text-[12.5px]"
          />
          <p className="mt-1.5 text-[11px] text-[var(--faint)]">{MODEL_COPY.customHint}</p>
        </div>
      )}

      <div className="mt-6 flex gap-3">
        <Button onClick={onContinue} disabled={!ready}>
          {WIZARD_COPY.continueToConfirm}
        </Button>
        <Button variant="ghost" onClick={onBack}>
          {WIZARD_COPY.back}
        </Button>
      </div>
    </div>
  );
}
