import { Badge } from "@/components/ui/badge";
import { VERDICT_COPY } from "@/copy";

export type Verdict = keyof typeof VERDICT_COPY;

/** Reliability verdict from the two normalized rates.
 *  reliable: correct in every repeat. inconsistent: some repeats pass (mean > pass^k) —
 *  the flakiness Tessera exists to surface. unreliable: fails the same way every time. */
export function verdictOf(passK: number, mean: number): Verdict {
  if (passK >= 1) return "reliable";
  return mean > passK ? "inconsistent" : "unreliable";
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
