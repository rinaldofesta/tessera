import { ChevronRight } from "lucide-react";
import { VerdictMosaic } from "@/components/VerdictMosaic";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { CONFIRM_COPY, WIZARD_COPY } from "@/copy";
import type { EvalSetupModel } from "@/types";

export interface RunDraft {
  org: string;
  model: string;
  judge: "llm" | "deterministic";
  grader: string | null;
  epochs: number;
}

interface ConfirmStepProps {
  draft: RunDraft;
  questions: number;
  models: EvalSetupModel[];
  onChange: (patch: Partial<RunDraft>) => void;
  onBack: () => void;
  onLaunch: () => void;
  launching: boolean;
  error: string | null;
}

export function ConfirmStep({
  draft,
  questions,
  models,
  onChange,
  onBack,
  onLaunch,
  launching,
  error,
}: ConfirmStepProps) {
  const selfGrading =
    draft.judge === "llm" && !!draft.grader && draft.grader === draft.model;
  const missingGrader = draft.judge === "llm" && !draft.grader;
  const blocked = selfGrading || missingGrader;

  return (
    <div>
      <h2 className="font-display text-2xl font-bold tracking-tight">
        {WIZARD_COPY.q3}
      </h2>
      <p className="mt-1 mb-5 text-sm text-[var(--muted-foreground)]">
        {CONFIRM_COPY.summary(questions, draft.epochs, draft.judge)}
      </p>

      <div className="flex flex-wrap items-start gap-7">
        <Card className="min-w-[320px] flex-1 p-4">
          <dl className="text-[13px]">
            {[
              [CONFIRM_COPY.suite, draft.org],
              [CONFIRM_COPY.model, draft.model],
              [
                CONFIRM_COPY.grading,
                draft.judge === "llm"
                  ? CONFIRM_COPY.llm
                  : CONFIRM_COPY.deterministic,
              ],
              [CONFIRM_COPY.repeats, CONFIRM_COPY.repeatsValue(draft.epochs)],
            ].map(([key, value], index, rows) => (
              <div key={key as string}>
                <div className="flex justify-between gap-6 py-1.5">
                  <dt className="text-[var(--muted-foreground)]">{key}</dt>
                  <dd className="text-right font-mono">{value}</dd>
                </div>
                {index < rows.length - 1 && <Separator />}
              </div>
            ))}
          </dl>
        </Card>
        <VerdictMosaic questions={questions} repeats={draft.epochs} />
      </div>

      <Collapsible className="mt-5">
        <CollapsibleTrigger className="group flex items-center gap-1.5 text-[13px] text-[var(--muted-foreground)] outline-none hover:text-[var(--foreground)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]">
          <ChevronRight className="size-3.5 transition-transform group-data-[state=open]:rotate-90 motion-reduce:transition-none" />
          {CONFIRM_COPY.advanced}
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-3 grid max-w-lg gap-4">
          <div className="grid gap-1.5">
            <Label>{CONFIRM_COPY.gradingLabel}</Label>
            <Select
              value={draft.judge}
              onValueChange={(value) =>
                onChange({ judge: value as RunDraft["judge"] })
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="deterministic">
                  {CONFIRM_COPY.deterministic}
                </SelectItem>
                <SelectItem value="llm">{CONFIRM_COPY.llm}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {draft.judge === "llm" && (
            <div className="grid gap-1.5">
              <Label>{CONFIRM_COPY.graderLabel}</Label>
              <Select
                value={draft.grader ?? ""}
                onValueChange={(value) => onChange({ grader: value })}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={CONFIRM_COPY.graderPlaceholder} />
                </SelectTrigger>
                <SelectContent>
                  {models
                    .filter(
                      (model) =>
                        model.readiness === "ready" ||
                        model.readiness === "unverified",
                    )
                    .map((model) => (
                      <SelectItem
                        key={model.id}
                        value={model.id}
                        disabled={model.id === draft.model}
                      >
                        {model.label}
                        {model.id === draft.model
                          ? CONFIRM_COPY.underTestSuffix
                          : ""}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              {(selfGrading || missingGrader) && (
                <p className="text-[11.5px] text-[var(--verdict-unreliable)]">
                  {selfGrading
                    ? CONFIRM_COPY.selfGrading
                    : CONFIRM_COPY.graderRequired}
                </p>
              )}
            </div>
          )}

          <div className="grid gap-1.5">
            <Label htmlFor="repeats">{CONFIRM_COPY.repeatsLabel}</Label>
            <Input
              id="repeats"
              type="number"
              min={1}
              max={10}
              value={draft.epochs}
              onChange={(event) =>
                onChange({
                  epochs: Math.max(
                    1,
                    Math.min(10, parseInt(event.target.value, 10) || 3),
                  ),
                })
              }
              className="w-28"
            />
            <p className="text-[11.5px] text-[var(--faint)]">
              {CONFIRM_COPY.repeatsHint}
            </p>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {error && (
        <p className="mt-4 text-[13px] text-[var(--verdict-unreliable)]">
          {error}
        </p>
      )}

      <div className="mt-6 flex gap-3">
        <Button onClick={onLaunch} disabled={blocked || launching}>
          {launching ? CONFIRM_COPY.launching : WIZARD_COPY.launch}
        </Button>
        <Button variant="ghost" onClick={onBack}>
          {WIZARD_COPY.back}
        </Button>
      </div>
    </div>
  );
}
