import React from "react";

/** Mono uppercase section eyebrow — the graphite successor of term.tsx's SectionLabel. */
export function SectionLabel({ children }: React.PropsWithChildren) {
  return (
    <div className="mb-2 font-mono text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
      {children}
    </div>
  );
}
