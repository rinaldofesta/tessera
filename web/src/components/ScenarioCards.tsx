import { useState } from "react";
import { conflictLabel, SUITE_COPY } from "@/copy";
import { ScenarioWizard } from "@/components/ScenarioWizard";
import { Button } from "@/components/ui/button";
import type { Claim, ProbeDef } from "@/types";

function ClaimLine({ claim, id }: { claim: Claim | undefined; id: string }) {
  if (!claim) return <span className="text-muted-foreground">{SUITE_COPY.cards.missingClaim(id)}</span>;
  return (
    <span>
      {claim.subject} — {claim.predicate}: {String(claim.value)} ({claim.silo}
      {claim.asserted_at ? `, as of ${claim.asserted_at}` : ""})
    </span>
  );
}

/** One card per test question, with the recipe wizard as the only authoring path. */
export function ScenarioCards({
  claims, probes, onInsert, onRemove, readOnly = false,
}: {
  claims: Claim[];
  probes: ProbeDef[];
  onInsert: (claims: Claim[], probe: ProbeDef) => void;
  /** Undo one insert: drops the probe and the claims only it referenced. */
  onRemove?: (probeId: string) => void;
  readOnly?: boolean;
}) {
  const [wizardOpen, setWizardOpen] = useState(false);
  const byId = new Map(claims.map((c) => [c.claim_id, c]));
  const referenced = new Set(probes.flatMap((p) => p.references ?? []));
  const unused = claims.filter((c) => !referenced.has(c.claim_id));

  return (
    <div className="space-y-3 p-3">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
          {SUITE_COPY.cards.scenarios(probes.length)}
        </span>
        {!readOnly && <Button size="xs" onClick={() => setWizardOpen(true)}>{SUITE_COPY.cards.newScenario}</Button>}
      </div>

      {probes.length === 0 ? (
        <div className="border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
          {SUITE_COPY.cards.empty}
          {!readOnly && (
            <div className="mt-3">
              <Button size="sm" onClick={() => setWizardOpen(true)}>{SUITE_COPY.cards.newScenario}</Button>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {probes.map((p) => (
            <div key={p.probe_id} className="border border-border p-2 text-xs">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="font-bold">{p.question}</span>
                <span className="flex shrink-0 items-center gap-1">
                  <span className="border border-border px-1 text-[10px] uppercase text-muted-foreground">
                    {conflictLabel(p.conflict_type)}
                  </span>
                  {!readOnly && onRemove && (
                    <button
                      type="button"
                      className="text-[10px] text-muted-foreground hover:text-foreground"
                      onClick={() => onRemove(p.probe_id)}
                    >
                      {SUITE_COPY.cards.remove}
                    </button>
                  )}
                </span>
              </div>
              <div className="text-muted-foreground">
                {p.expected_behavior === "answer" ? SUITE_COPY.cards.answer(p.expected_answer ?? "") : SUITE_COPY.cards.refuse}
              </div>
              {p.conflict_type === "void" ? (
                <div className="mt-1 text-muted-foreground">{SUITE_COPY.cards.noFacts}</div>
              ) : (
                <ul className="mt-1 space-y-0.5 text-muted-foreground">
                  {(p.references ?? []).map((id) => (
                    <li key={id}><ClaimLine claim={byId.get(id)} id={id} /></li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}

      {unused.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
            {SUITE_COPY.cards.unusedFacts(unused.length)}
          </div>
          <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
            {unused.map((c) => (
              <li key={c.claim_id}>{c.subject} — {c.predicate}: {String(c.value)} ({c.silo})</li>
            ))}
          </ul>
        </div>
      )}

      {!readOnly && (
        <ScenarioWizard
          open={wizardOpen}
          onOpenChange={setWizardOpen}
          claims={claims}
          probes={probes}
          onInsert={(newClaims, newProbe) => { onInsert(newClaims, newProbe); setWizardOpen(false); }}
        />
      )}
    </div>
  );
}
