import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DATASET_DESCRIPTIONS, DATASET_LABELS, WIZARD_COPY } from "@/copy";
import { cn } from "@/lib/utils";
import type { EvalSetup } from "@/types";

interface SuiteStepProps {
  suites: EvalSetup["suites"];
  value?: string;
  onChange: (id: string) => void;
  onContinue: () => void;
}

export function SuiteStep({ suites, value, onChange, onContinue }: SuiteStepProps) {
  return (
    <div>
      <h2 className="font-display text-2xl font-bold tracking-tight">{WIZARD_COPY.q1}</h2>
      <p className="mt-1 mb-5 text-sm text-[var(--muted-foreground)]">{WIZARD_COPY.q1sub}</p>

      <div
        role="radiogroup"
        aria-label={WIZARD_COPY.q1}
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
      >
        {suites.map((suite) => {
          const selected = suite.id === value;

          return (
            <Card
              key={suite.id}
              role="radio"
              tabIndex={0}
              aria-checked={selected}
              onClick={() => onChange(suite.id)}
              onKeyDown={(event) => {
                if (event.key === " " || event.key === "Enter") {
                  event.preventDefault();
                  onChange(suite.id);
                }
              }}
              className={cn(
                // flex column + mt-auto on the meta keeps every card in a row the same
                // height with its footer aligned, even when a custom suite has no description.
                "flex cursor-pointer flex-col p-4 transition-colors outline-none",
                "focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
                selected
                  ? "border-[var(--primary)] shadow-[inset_0_0_0_1px_var(--primary)]"
                  : "hover:border-[color-mix(in_oklab,var(--primary)_40%,var(--border))]",
              )}
            >
              <h3 className="font-display text-[15px] font-bold">
                {DATASET_LABELS[suite.id] ?? suite.id}
              </h3>
              {DATASET_DESCRIPTIONS[suite.id] && (
                <p className="mt-1.5 text-[12.5px] leading-relaxed text-[var(--muted-foreground)]">
                  {DATASET_DESCRIPTIONS[suite.id]}
                </p>
              )}
              <p className="mt-auto pt-3 font-mono text-[10.5px] text-[var(--faint)]">
                {WIZARD_COPY.suiteMeta(suite.questions, suite.kind)}
              </p>
            </Card>
          );
        })}
      </div>

      <div className="mt-6 flex gap-3">
        <Button onClick={onContinue} disabled={!value}>
          {WIZARD_COPY.continueToModel}
        </Button>
      </div>
    </div>
  );
}
