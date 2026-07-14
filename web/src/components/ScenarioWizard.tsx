import { useEffect, useState } from "react";
import { api } from "@/api";
import { conflictLabel, RECIPE_CONFLICT, RECIPES, type RecipeKey } from "@/copy";
import { RECIPE_SPECS } from "@/lib/scenarioRecipes";
import { Field, FieldLabel, ValidationErrors } from "@/components/form";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { Blueprint, Claim, ProbeDef, ValidationResult } from "@/types";

type Step = "pick" | "fill" | "review";

/** 3-step "for dummies" scenario builder: pick a recipe, answer plain questions,
    review the generated claims+probe (editable, preflighted) before inserting. */
export function ScenarioWizard({
  open, onOpenChange, claims, probes, onInsert,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  claims: Claim[];
  probes: ProbeDef[];
  onInsert: (claims: Claim[], probe: ProbeDef) => void;
}) {
  const [step, setStep] = useState<Step>("pick");
  const [recipeKey, setRecipeKey] = useState<RecipeKey | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [preflight, setPreflight] = useState<ValidationResult | null>(null);

  // a fresh wizard every time it opens — no cross-run state to reason about
  useEffect(() => {
    if (!open) {
      setStep("pick");
      setRecipeKey(null);
      setFields({});
      setPreflight(null);
    }
  }, [open]);

  const spec = recipeKey ? RECIPE_SPECS[recipeKey] : null;
  // generate() assumes fully-populated (post-defaults) fields, which is only true
  // once "next" has run defaults() — never call it against the mid-fill draft
  const existingIds = new Set([...claims.map((c) => c.claim_id), ...probes.map((p) => p.probe_id)]);
  const draft = spec && step === "review" ? spec.generate(fields, existingIds) : null;
  const warnings = spec && draft ? spec.warn(fields, { claims, probes }) : [];

  // preflight = the real validate endpoint against existing + draft, on entry and on edits
  useEffect(() => {
    if (step !== "review" || !draft) return;
    let alive = true;
    const candidate: Blueprint = { claims: [...claims, ...draft.claims], probes: [...probes, draft.probe] };
    const t = setTimeout(() => {
      api
        .validateBlueprint(candidate)
        .then((v) => { if (alive) setPreflight(v); })
        .catch(() => {
          if (alive)
            setPreflight({ ok: false, errors: [{ location: "(api)", message: "validation request failed — backend unreachable?" }] });
        });
    }, 400);
    return () => { alive = false; clearTimeout(t); };
    // re-run whenever the draft's content changes (fields edited at review)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, JSON.stringify(draft)]);

  function pick(key: RecipeKey) {
    setRecipeKey(key);
    setFields({});
    setStep("fill");
  }
  function next() {
    if (!spec) return;
    setFields(spec.defaults(fields));
    setPreflight(null);
    setStep("review");
  }
  function insert() {
    if (!draft) return;
    onInsert(draft.claims, draft.probe);
    onOpenChange(false);
  }
  const set = (key: string) => (v: string) => setFields((f) => ({ ...f, [key]: v }));
  const missingRequired = spec?.fields.some((f) => f.required && !(fields[f.key] ?? "").trim());

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {step === "pick" && "new scenario — pick a situation"}
            {step === "fill" && spec && RECIPES[spec.key].title}
            {step === "review" && "review before inserting"}
          </DialogTitle>
        </DialogHeader>

        {step === "pick" && (
          <div className="grid gap-2 sm:grid-cols-2">
            {(Object.keys(RECIPES) as RecipeKey[]).map((key) => (
              <button
                key={key}
                onClick={() => pick(key)}
                className="border border-border p-3 text-left hover:bg-muted"
              >
                <div className="mb-1">
                  <div className="text-sm font-bold">{RECIPES[key].title}</div>
                  <span className="mt-1 inline-block border border-border px-1 text-[10px] uppercase text-muted-foreground">
                    {conflictLabel(RECIPE_CONFLICT[key])}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{RECIPES[key].blurb}</p>
                <p className="mt-1 text-[11px] text-muted-foreground italic">{RECIPES[key].example}</p>
              </button>
            ))}
          </div>
        )}

        {step === "fill" && spec && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {spec.fields.map((f) => (
                <Field
                  key={f.key}
                  label={f.required ? f.label : `${f.label} (optional)`}
                  value={fields[f.key] ?? ""}
                  placeholder={f.placeholder}
                  onChange={set(f.key)}
                />
              ))}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setStep("pick")}>back</Button>
              <Button disabled={missingRequired} onClick={next}>next</Button>
            </DialogFooter>
          </div>
        )}

        {step === "review" && spec && draft && (
          <div className="space-y-3">
            {draft.claims.length === 0 ? (
              <div className="border border-border p-2 text-xs text-muted-foreground">
                no facts generated for this scenario — the question stands on its own, unanswerable by design.
              </div>
            ) : (
              draft.claims.map((c, i) => (
                <div key={c.claim_id} className="border border-border p-2 text-xs">
                  <div className="mb-1 text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                    fact {i + 1} — {c.silo}
                  </div>
                  <div>{c.subject} — {c.predicate}: {String(c.value)}</div>
                  {c.asserted_at && <div className="text-muted-foreground">as of {c.asserted_at}</div>}
                  {c.render.as === "prose" && (
                    <div className="mt-1.5">
                      <Field
                        label="sentence template — {value} is replaced by the value"
                        value={c.render.template ?? ""}
                        onChange={(v) => setFields((f) => ({ ...f, template: v }))}
                      />
                    </div>
                  )}
                </div>
              ))
            )}

            {spec.key === "recency" && (
              <div className="grid grid-cols-2 gap-2">
                <Field label="as of (crm, older)" value={fields.assertedAtA ?? ""} onChange={set("assertedAtA")} />
                <Field label="as of (docs, newer)" value={fields.assertedAtB ?? ""} onChange={set("assertedAtB")} />
              </div>
            )}

            <div className="border border-border p-2 text-xs">
              <div className="mb-1 flex justify-end">
                <span className="border border-border px-1 text-[10px] uppercase text-muted-foreground">
                  {conflictLabel(draft.probe.conflict_type)}
                </span>
              </div>
              <Field label="question" value={fields.question ?? ""} onChange={set("question")} />
              {draft.probe.expected_behavior === "answer" ? (
                <div className="mt-1.5">
                  <Field label="expected answer" value={fields.expected_answer ?? ""} onChange={set("expected_answer")} />
                </div>
              ) : (
                <div className="mt-1.5 text-muted-foreground">→ must refuse — no answer to give</div>
              )}
            </div>

            {warnings.length > 0 && (
              <div className="space-y-1 border border-dashed border-border p-2 text-xs text-muted-foreground">
                {warnings.map((w, i) => <div key={i}>⚠ {w}</div>)}
              </div>
            )}

            <div>
              <FieldLabel>preflight — a real validate call against the full blueprint</FieldLabel>
              {!preflight ? (
                <div className="text-xs text-muted-foreground">checking…</div>
              ) : preflight.ok ? (
                <div className="text-xs">✓ valid</div>
              ) : (
                <ValidationErrors errors={preflight.errors} />
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setStep("fill")}>back</Button>
              <Button onClick={insert}>insert</Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
