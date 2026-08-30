import React from "react";
import { cn } from "@/lib/utils";

/** Mono uppercase section eyebrow — the graphite successor of term.tsx's SectionLabel. */
export function SectionLabel({
  children,
  className,
}: React.PropsWithChildren<{ className?: string }>) {
  return (
    <div
      className={cn(
        "mb-2 font-mono text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground",
        className,
      )}
    >
      {children}
    </div>
  );
}
