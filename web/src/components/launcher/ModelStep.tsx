import { RefreshCw } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MODEL_COPY, PROVIDER_LABELS, WIZARD_COPY } from "@/copy";
import { cn } from "@/lib/utils";
import type { EvalSetupModel, SourceStatus } from "@/types";

const SELECTABLE = new Set<EvalSetupModel["readiness"]>(["ready", "unverified"]);
const LOCAL = new Set(["mlx", "ollama"]);
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
  const [query, setQuery] = useState("");
  const usable = models.filter((model) => SELECTABLE.has(model.readiness));
  // Local models are the user's own: hiding them means they cannot discover what is on
  // their machine. Shown, but never selectable until something confirms a server answers —
  // offering an unserved model is the false-ready bug this phase removed.
  const local = models.filter(
    (model) => !SELECTABLE.has(model.readiness) && LOCAL.has(model.provider),
  );
  const hidden = models.length - usable.length - local.length;
  // "discovered" used to mean "local", because cloud was a fixed catalogue. Now that the
  // cloud list is live, most discovered models are remote — so group by where a model
  // actually comes from, not by whether we happened to curate it.
  const needle = query.trim().toLowerCase();
  const matches = (m: EvalSetupModel) => !needle || m.id.toLowerCase().includes(needle);
  const shown = usable.filter(matches);
  const shownLocal = local.filter(matches);
  const groups = [
    { key: "published", label: MODEL_COPY.publishedGroup, items: shown.filter((m) => m.published) },
    {
      key: "cloud",
      label: MODEL_COPY.providerGroup,
      items: shown.filter((m) => !m.published && !LOCAL.has(m.provider)),
    },
    {
      key: "machine",
      label: MODEL_COPY.machineGroup,
      items: shown.filter((m) => !m.published && LOCAL.has(m.provider)),
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

      <Input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={MODEL_COPY.filterPlaceholder}
        aria-label={MODEL_COPY.filterPlaceholder}
        className="mb-3 font-mono text-[12.5px]"
      />

      <div
        role="radiogroup"
        aria-label={WIZARD_COPY.q2}
        className="overflow-hidden rounded-lg border border-[var(--border)]"
      >
        {groups.map((group) => (
          <div key={group.key}>
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
                  {model.retired ? (
                    <Badge
                      variant="outline"
                      className="border-[var(--border)] text-[var(--faint)]"
                    >
                      {MODEL_COPY.retired}
                    </Badge>
                  ) : null}
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

        {shownLocal.length > 0 && (
          <div>
            <p className="border-b border-t border-[var(--border)] bg-[#101216] px-3.5 pt-2.5 pb-1.5 font-mono text-[10.5px] uppercase tracking-[0.12em] text-[var(--faint)]">
              {MODEL_COPY.localGroup}
            </p>
            {shownLocal.map((model) => (
              <div
                key={model.id}
                className="flex items-center gap-3 border-b border-[var(--border)] bg-[#191b21] px-3.5 py-2.5 last:border-b-0"
              >
                <span className="min-w-0 flex-1 truncate font-mono text-[12.5px] text-[var(--faint)]">
                  {model.label}
                </span>
                {model.detail ? (
                  <button
                    type="button"
                    onClick={() => navigator.clipboard?.writeText(model.detail ?? "")}
                    className="rounded-md px-1 font-mono text-[10.5px] text-[var(--primary)] outline-none hover:underline focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                  >
                    {MODEL_COPY.copyCommand}
                  </button>
                ) : null}
                <Badge
                  variant="outline"
                  className="border-[var(--border)] text-[var(--faint)]"
                >
                  {model.readiness === "needs_server"
                    ? MODEL_COPY.needsServer
                    : MODEL_COPY.runtimeOffline}
                </Badge>
              </div>
            ))}
          </div>
        )}

        {groups.length === 0 && shownLocal.length === 0 && (
          <p className="border-b border-[var(--border)] bg-[var(--card)] px-3.5 py-4 text-center text-[12.5px] text-[var(--muted-foreground)]">
            {MODEL_COPY.noMatch}
          </p>
        )}

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
