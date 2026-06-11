import React from "react";
import { cn } from "@/lib/utils";

/** View title rendered as a shell prompt. */
export function ViewHeader({ cmd, desc }: { cmd: string; desc: string }) {
  return (
    <div className="mb-5">
      <h1 className="text-base font-semibold tracking-tight">
        <span className="select-none text-muted-foreground">$ </span>
        {cmd}
      </h1>
      <p className="mt-0.5 text-xs text-muted-foreground">{desc}</p>
    </div>
  );
}

/** Bordered section with an uppercase header strip — the basic inspector panel. */
export function Panel({
  title,
  right,
  className,
  bodyClassName,
  children,
}: React.PropsWithChildren<{
  title?: string;
  right?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}>) {
  return (
    <section className={cn("border border-border bg-card", className)}>
      {title && (
        <header className="flex h-8 shrink-0 items-center justify-between gap-2 border-b border-border px-3">
          <span className="truncate text-[10px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
            {title}
          </span>
          {right}
        </header>
      )}
      <div className={cn("p-3", bodyClassName)}>{children}</div>
    </section>
  );
}

/** Run lifecycle token: [done] [run…] [err!] */
export function StatusToken({ status }: { status: string }) {
  if (status === "done")
    return <span className="border border-border px-1 text-[10px] uppercase text-foreground">✓ done</span>;
  if (status === "error")
    return <span className="bg-foreground px-1 text-[10px] font-bold uppercase text-background">err!</span>;
  return (
    <span className="animate-pulse border border-border px-1 text-[10px] uppercase text-muted-foreground">
      run…
    </span>
  );
}

/** Grade token. Inversion is reserved for failure — the loudest monochrome
    signal belongs to the thing a reliability tool exists to surface. */
export function GradeToken({ passK, flaky }: { passK: number; flaky: boolean }) {
  if (passK >= 1)
    return <span className="border border-border px-1.5 text-[10px] font-bold uppercase">✓ pass</span>;
  if (flaky)
    return (
      <span className="border border-dashed border-foreground px-1.5 text-[10px] font-bold uppercase">
        ~ flaky
      </span>
    );
  return <span className="bg-foreground px-1.5 text-[10px] font-bold uppercase text-background">✗ fail</span>;
}

export function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="border border-border bg-card px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-bold tabular-nums">{value}</div>
      {sub && <div className="truncate text-[10px] text-muted-foreground">{sub}</div>}
    </div>
  );
}

/** Horizontal meter: white fill on black track; hatched when flaky. */
export function MeterBar({ value, flaky }: { value: number; flaky?: boolean }) {
  const w = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="h-2.5 w-full border border-border bg-background">
      <div
        className={cn("h-full bg-foreground")}
        style={
          flaky
            ? {
                width: `${w}%`,
                background:
                  "repeating-linear-gradient(45deg, var(--foreground), var(--foreground) 3px, transparent 3px, transparent 6px)",
              }
            : { width: `${w}%` }
        }
      />
    </div>
  );
}

export function ErrLine({ msg }: { msg: string }) {
  return (
    <div className="flex items-start gap-2 border border-foreground/60 px-3 py-2 text-xs whitespace-pre-wrap">
      <span className="bg-foreground px-1 font-bold text-background">ERR</span>
      <span className="min-w-0 break-words">{msg}</span>
    </div>
  );
}

export function SectionLabel({ children }: React.PropsWithChildren) {
  return (
    <div className="mb-1 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{children}</div>
  );
}
