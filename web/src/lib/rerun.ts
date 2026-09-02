import type { Run } from "@/types";

export function rerunHref(run: Run): string {
  const request = run.request;
  const params = new URLSearchParams([
    ["model", request.model],
    ["suite", request.suite],
    ["k", String(request.k)],
    ["engine", request.engine],
    ["grader", request.grader ?? ""],
    ["scaffold", request.scaffold],
    ["seed", String(request.seed)],
  ]);
  return `/?${params.toString()}`;
}
