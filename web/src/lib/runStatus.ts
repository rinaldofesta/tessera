import type { Run, RunStatus } from "@/types";

/** Map the 0.3 run status vocabulary onto the one the current views still render. */
export function toLegacyStatus(status: Run["status"]): RunStatus["status"] {
  if (status === "queued" || status === "running") return "running";
  if (status === "completed") return "done";
  return "error";
}
