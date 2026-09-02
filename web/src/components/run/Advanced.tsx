import { ChevronRight } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RUN_COPY } from "@/copy";
import type { CatalogModel, RunSpec } from "@/types";

interface AdvancedProps {
  spec: RunSpec;
  models: CatalogModel[];
  scaffolds: string[];
  initialOpen: boolean;
  onChange: (patch: Partial<RunSpec>) => void;
}

export function Advanced({ spec, models, scaffolds, initialOpen, onChange }: AdvancedProps) {
  const selfGrading = spec.engine === "llm" && spec.grader === spec.model;
  const missingGrader = spec.engine === "llm" && !spec.grader;
  const selectClass = "h-8 rounded-lg border border-line bg-raised px-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40";

  return (
    <Collapsible className="mt-6" defaultOpen={initialOpen}>
      <CollapsibleTrigger className="group flex items-center gap-1.5 text-sm text-faint outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary">
        <ChevronRight className="size-4 transition-transform group-data-[state=open]:rotate-90" />
        {RUN_COPY.advanced}
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-4 grid max-w-xl gap-4 rounded-xl border border-line bg-panel p-4">
        <fieldset className="grid gap-2">
          <legend className="text-sm font-medium">{RUN_COPY.engine}</legend>
          <div className="flex flex-wrap gap-4">
            {(["deterministic", "llm"] as const).map((engine) => (
              <Label key={engine} className="flex items-center gap-2 font-normal">
                <input type="radio" name="engine" value={engine} checked={spec.engine === engine}
                  onChange={() => onChange({ engine })} />
                {engine === "deterministic" ? RUN_COPY.deterministic : RUN_COPY.llm}
              </Label>
            ))}
          </div>
        </fieldset>
        {spec.engine === "llm" && (
          <div className="grid gap-1.5">
            <Label htmlFor="grader-model">{RUN_COPY.grader}</Label>
            <select id="grader-model" className={selectClass} value={spec.grader ?? ""}
              onChange={(event) => onChange({ grader: event.target.value || null })}>
              <option value="">{RUN_COPY.chooseGrader}</option>
              {models.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}
            </select>
            {(selfGrading || missingGrader) && (
              <p className="text-xs text-verdict-unreliable">
                {selfGrading ? RUN_COPY.selfGrading : RUN_COPY.graderRequired}
              </p>
            )}
          </div>
        )}
        <div className="grid gap-1.5">
          <Label htmlFor="scaffold">{RUN_COPY.scaffold}</Label>
          <select id="scaffold" className={selectClass} value={spec.scaffold}
            onChange={(event) => onChange({ scaffold: event.target.value })}>
            {scaffolds.map((scaffold) => <option key={scaffold}>{scaffold}</option>)}
          </select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="seed">{RUN_COPY.seed}</Label>
          <Input id="seed" type="number" min={0} className="w-28 bg-raised" value={spec.seed}
            onChange={(event) => onChange({ seed: Math.max(0, Number(event.target.value) || 0) })} />
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
