import { MOSAIC_COPY } from "@/copy";
import { cn } from "@/lib/utils";
import type { Report } from "@/types";

export type TileState = "pending" | "pass" | "fail";

/** Lay out repeats as rows so each failed epoch lands on its actual tile. */
export function tilesFrom(report: Report): TileState[] {
  const repeats = report.probes[0]?.epochs_total ?? report.header.k;
  return Array.from({ length: repeats }, (_, repeat) =>
    report.probes.map((probe) =>
      probe.failures.some((failure) => failure.epoch === repeat + 1) ? "fail" : "pass",
    ),
  ).flat();
}

interface VerdictMosaicProps {
  questions: number;
  repeats: number;
  /** One entry per tile, row-major. Omit while the run is in flight. */
  tiles?: TileState[];
  label?: string;
  /** md: row-height tiles (34px columns). lg: detail-page tiles (44px columns). */
  size?: "md" | "lg";
}

const TILE: Record<TileState, string> = {
  pending: "border-[var(--line)] bg-[var(--raised)]",
  pass: "border-[var(--verdict-reliable)]/55 bg-[var(--verdict-reliable)]/22",
  fail: "border-[var(--verdict-unreliable)]/55 bg-[var(--verdict-unreliable)]/22",
};

/** One tile per answer — questions across, repeats down. The count is the honest
 * statement of scale: no percentage is invented while the run is in flight. */
export function VerdictMosaic({
  questions,
  repeats,
  tiles,
  label,
  size = "md",
}: VerdictMosaicProps): JSX.Element {
  const total = Math.max(0, questions) * Math.max(0, repeats);
  const col = size === "lg" ? 44 : 34;
  const states: TileState[] = Array.from(
    { length: total },
    (_, index) => tiles?.[index] ?? "pending",
  );

  return (
    <figure className="m-0">
      <div
        className="grid gap-[3px]"
        style={{
          gridTemplateColumns: `repeat(${Math.max(1, questions)}, minmax(0, 1fr))`,
          maxWidth: `${Math.max(1, questions) * col}px`,
        }}
        role="img"
        aria-label={label ?? MOSAIC_COPY.aria(questions, repeats)}
      >
        {states.map((state, index) => (
          <span
            key={index}
            className={cn(
              "aspect-square rounded-[3px] border transition-colors duration-500 motion-reduce:transition-none",
              TILE[state],
            )}
          />
        ))}
      </div>
      <figcaption className="mt-2.5 font-mono text-[11px] text-[var(--faint)]">
        {tiles
          ? MOSAIC_COPY.resolved(
              states.filter((s) => s === "pass").length, total, questions, repeats)
          : MOSAIC_COPY.caption(questions, repeats, total)}
      </figcaption>
    </figure>
  );
}
