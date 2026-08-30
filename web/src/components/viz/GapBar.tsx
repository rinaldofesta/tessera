import { GAP_COPY } from "@/copy";
import { pct } from "@/lib/format";
import { cn } from "@/lib/utils";

interface GapBarProps {
  /** Rate that passed every repeat (pass^k), normalized 0…1. */
  passK: number;
  /** Mean success rate across repeats, normalized 0…1. Must be ≥ passK. */
  mean: number;
  /** Repeat count, for the aria sentence. */
  k: number;
  className?: string;
}

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

export function gapPoints(passK: number, mean: number): number {
  const p = clamp01(passK);
  const m = Math.max(clamp01(mean), p);
  return Math.round((m - p) * 100);
}

/** The core reliability glyph. Solid fill 0→pass^k (iris; green only at exactly 1),
 *  hatched amber pass^k→mean (passes only sometimes — the gap IS the finding),
 *  dark remainder mean→1 (fails even on average). Gap is stated in percentage points. */
export function GapBar({ passK, mean, k, className }: GapBarProps) {
  if (import.meta.env.DEV && passK > mean + 1e-9) {
    console.warn(`GapBar: passK (${passK}) > mean (${mean}) — inconsistent rates, gap clamped to 0`);
  }
  const p = clamp01(passK);
  const m = Math.max(clamp01(mean), p);
  const gapPp = gapPoints(passK, mean);

  return (
    <div
      role="img"
      aria-label={GAP_COPY.aria(pct(p), k, pct(m), gapPp)}
      className={cn("flex h-2.5 w-full overflow-hidden rounded-full bg-[var(--raised)]", className)}
    >
      <div
        data-seg="pass"
        className={cn("h-full", p >= 1 ? "bg-verdict-reliable" : "bg-primary")}
        style={{ width: `${parseFloat((p * 100).toFixed(4))}%` }}
      />
      <div
        data-seg="gap"
        className="h-full"
        style={{
          width: `${parseFloat((Math.max(m - p, 0) * 100).toFixed(4))}%`,
          background:
            "repeating-linear-gradient(45deg, color-mix(in srgb, var(--verdict-inconsistent) 60%, transparent) 0 3px, transparent 3px 6px)",
        }}
      />
    </div>
  );
}
