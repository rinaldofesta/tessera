import { type RunDraft } from "@/components/launcher/ConfirmStep";
import { CUSTOM } from "@/components/launcher/ModelStep";
import type { RunSummary } from "@/types";

/** Launcher prefill for "Rerun": copy a past run's config. A model that's no longer
 *  in the offered list lands in the custom-model slot instead of a dead dropdown value. */
export function draftFromRun(
  run: RunSummary,
  knownModelIds: string[],
): { draft: RunDraft; customId: string | null } {
  const known = knownModelIds.includes(run.model);
  return {
    draft: {
      org: run.org,
      model: known ? run.model : CUSTOM,
      judge: run.judge === "llm" ? "llm" : "deterministic",
      grader: run.grader,
      epochs: run.epochs,
    },
    customId: known ? null : run.model,
  };
}
