import { Badge } from "@/components/ui/badge";
import { REPORT_COPY, VERDICT_COPY } from "@/copy";
import type { Report } from "@/types";

export type Verdict = keyof typeof VERDICT_COPY;

/** Reliability verdict from the two normalized rates.
 *  reliable: correct in every repeat. inconsistent: some repeats pass (mean > pass^k) —
 *  the flakiness Tessera exists to surface. unreliable: fails the same way every time. */
export function verdictOf(passK: number, mean: number): Verdict {
  if (passK >= 1) return "reliable";
  return mean > passK ? "inconsistent" : "unreliable";
}

type Failure = Report["probes"][number]["failures"][number];

/** Why one repeat of a probe failed, shared by the on-screen and exported details. */
export function whyFailed(expected: string, f: Failure): string {
  if (expected === "refuse" && !f.refusal_ok) return REPORT_COPY.whyRefuseMissed;
  if (expected === "refuse" && f.refusal_ok && !f.provenance_ok) return REPORT_COPY.whyRefusalProvenance;
  if (!f.accuracy_ok) return REPORT_COPY.whyWrongAnswer;
  if (!f.provenance_ok) return REPORT_COPY.whyProvenance;
  return REPORT_COPY.whyGeneric;
}

const STYLE: Record<Verdict, string> = {
  reliable: "border-verdict-reliable/55 text-verdict-reliable",
  inconsistent: "border-verdict-inconsistent/55 text-verdict-inconsistent",
  unreliable: "border-verdict-unreliable/55 text-verdict-unreliable",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <Badge variant="outline" className={STYLE[verdict]}>
      {VERDICT_COPY[verdict]}
    </Badge>
  );
}
