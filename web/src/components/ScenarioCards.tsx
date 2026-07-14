import { useState } from "react";
import { conflictLabel } from "@/copy";
import { ScenarioWizard } from "@/components/ScenarioWizard";
import { Button } from "@/components/ui/button";
import type { Claim, ProbeDef } from "@/types";

function ClaimLine({ claim, id }: { claim: Claim | undefined; id: string }) {
  if (!claim) return <span className="text-muted-foreground">‹missing claim: {id}›</span>;
  return (
    <span>
      {claim.subject} — {claim.predicate}: {String(claim.value)} ({claim.silo}
      {claim.asserted_at ? `, as of ${claim.asserted_at}` : ""})
    </span>
  );
}

/** The default simple view: one card per test question (probe), plain-language,
    with the wizard as the only way in. Advanced mode (Datasets.tsx) still edits
    the raw rows behind these cards. */
export function ScenarioCards({
  claims, probes, onInsert,
}: {
  claims: Claim[];
  probes: ProbeDef[];
  onInsert: (claims: Claim[], probe: ProbeDef) => void;
}) {
  const [wizardOpen, setWizardOpen] = useState(false);
  const byId = new Map(claims.map((c) => [c.claim_id, c]));
  const referenced = new Set(probes.flatMap((p) => p.references ?? []));
  const unused = claims.filter((c) => !referenced.has(c.claim_id));

  return (
    <div className="space-y-3 p-3">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
          scenarios [{probes.length}]
        </span>
        <Button size="xs" onClick={() => setWizardOpen(true)}>+ new scenario</Button>
      </div>

      {probes.length === 0 ? (
        <div className="border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
          no scenarios yet — a scenario is one test question plus the facts behind it.
          <div className="mt-3">
            <Button size="sm" onClick={() => setWizardOpen(true)}>+ new scenario</Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {probes.map((p) => (
            <div key={p.probe_id} className="border border-border p-2 text-xs">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="font-bold">{p.question}</span>
                <span className="shrink-0 border border-border px-1 text-[10px] uppercase text-muted-foreground">
                  {conflictLabel(p.conflict_type)}
                </span>
              </div>
              <div className="text-muted-foreground">
                {p.expected_behavior === "answer" ? `→ answer: ${p.expected_answer ?? ""}` : "→ must refuse"}
              </div>
              {p.conflict_type === "void" ? (
                <div className="mt-1 text-muted-foreground">(no facts — correctly absent)</div>
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
            unused facts [{unused.length}]
          </div>
          <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
            {unused.map((c) => (
              <li key={c.claim_id}>{c.subject} — {c.predicate}: {String(c.value)} ({c.silo})</li>
            ))}
          </ul>
        </div>
      )}

      <ScenarioWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        claims={claims}
        probes={probes}
        onInsert={(newClaims, newProbe) => { onInsert(newClaims, newProbe); setWizardOpen(false); }}
      />
    </div>
  );
}
