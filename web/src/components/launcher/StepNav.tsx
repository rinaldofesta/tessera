import { Check } from "lucide-react";
import { WIZARD_COPY } from "@/copy";
import { cn } from "@/lib/utils";

export type StepId = 1 | 2 | 3;

interface StepNavProps {
  current: StepId;
  chosen: { suite?: string; model?: string };
  onJump: (step: StepId) => void;
}

export function StepNav({ current, chosen, onJump }: StepNavProps) {
  const steps: { id: StepId; label: string; done?: string }[] = [
    { id: 1, label: WIZARD_COPY.step1, done: chosen.suite },
    { id: 2, label: WIZARD_COPY.step2, done: chosen.model },
    { id: 3, label: WIZARD_COPY.step3 },
  ];

  return (
    <ol className="mb-7 flex flex-wrap items-center gap-x-5 gap-y-2 font-mono text-[11.5px]">
      {steps.map((step) => {
        const isDone = step.id < current;
        const isCurrent = step.id === current;

        return (
          <li key={step.id}>
            <button
              type="button"
              disabled={step.id > current}
              onClick={() => onJump(step.id)}
              className={cn(
                "flex items-center gap-2 rounded-md px-1 py-1 outline-none",
                "focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
                isCurrent && "text-[var(--primary)]",
                isDone && "text-[var(--muted-foreground)] hover:text-[var(--foreground)]",
                !isCurrent && !isDone && "cursor-not-allowed text-[var(--faint)]",
              )}
            >
              <span
                className={cn(
                  "flex size-[19px] flex-none items-center justify-center rounded-full border text-[10px]",
                  isCurrent &&
                    "border-[var(--primary)] bg-[var(--primary)] text-[var(--primary-foreground)]",
                  isDone && "border-current bg-[var(--raised)]",
                  !isCurrent && !isDone && "border-current",
                )}
              >
                {isDone ? <Check className="size-3" /> : step.id}
              </span>
              {isDone && step.done ? step.done : step.label}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
