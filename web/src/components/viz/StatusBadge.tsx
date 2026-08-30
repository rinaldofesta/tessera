import { Badge } from "@/components/ui/badge";
import { STATUS_COPY } from "@/copy";
import { cn } from "@/lib/utils";

export type RunLifecycle = keyof typeof STATUS_COPY;

const STYLE: Record<RunLifecycle, string> = {
  running: "border-primary/55 text-primary",
  done: "border-border text-muted-foreground",
  error: "border-verdict-unreliable/55 text-verdict-unreliable",
};

/** Lifecycle only: running / finished / failed. Never a reliability verdict —
 *  that's VerdictBadge's job, which is why "done" stays neutral. */
export function StatusBadge({ status }: { status: RunLifecycle }) {
  return (
    <Badge variant="outline" className={cn(STYLE[status], status === "running" && "animate-pulse")}>
      {STATUS_COPY[status]}
    </Badge>
  );
}
