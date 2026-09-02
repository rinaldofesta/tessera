import type {
  Artifacts, Blueprint, BlueprintMeta, Catalog, ComparisonIntervention, ComparisonResult,
  Plan, Provider, ProviderUpdate, Run, RunSpec, ValidationResult,
} from "./types";

function messageForDetail(detail: unknown): string {
  if (Array.isArray(detail) && detail.every(
    (blocker) => typeof blocker === "object" && blocker !== null &&
      typeof (blocker as { message?: unknown }).message === "string",
  )) {
    return detail.map((blocker) => (blocker as { message: string }).message).join("; ");
  }
  return typeof detail === "string" ? detail : JSON.stringify(detail);
}

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
    throw new ApiError(messageForDetail(detail), res.status, detail);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(message: string, public status: number, public detail: unknown) {
    super(message);
  }
}

export const api = {
  compareRuns: (a: string, b: string, intervention: ComparisonIntervention = "model") =>
    fetch("/api/comparisons", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ a, b, intervention }),
    }).then(j<ComparisonResult>),

  // catalog + providers + runs
  catalog: () => fetch("/api/catalog").then(j<Catalog>),
  saveProvider: (id: string, body: ProviderUpdate) =>
    fetch(`/api/providers/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<Provider>),
  startRun: (spec: RunSpec) =>
    fetch("/api/runs", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(spec),
    }).then(j<Run>),
  dryRun: (spec: RunSpec) =>
    fetch("/api/runs/dry-run", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(spec),
    }).then(j<Plan>),
  getRun: (id: string) =>
    fetch(`/api/runs/${encodeURIComponent(id)}`).then(j<Run>),
  // EventSource isn't fetch-shaped, but network access still routes through this module.
  watchRun: (id: string) => new EventSource(`/api/runs/${id}/events`),
  listRuns: (includeArchived = false) =>
    fetch(`/api/runs${includeArchived ? "?include_archived=true" : ""}`)
      .then(j<Run[]>),
  setRunArchived: (id: string, archived: boolean) =>
    fetch(`/api/runs/${encodeURIComponent(id)}/archive`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ archived }),
    }).then(j<Run>),
  // blueprints (datasets)
  listBlueprints: () => fetch("/api/blueprints").then(j<BlueprintMeta[]>),
  getBlueprint: (id: string) => fetch(`/api/blueprints/${encodeURIComponent(id)}`).then(j<Blueprint>),
  validateBlueprint: (bp: Blueprint) =>
    fetch("/api/blueprints/validate", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(bp) }).then(j<ValidationResult>),
  previewBlueprint: (bp: Blueprint) =>
    fetch("/api/blueprints/preview", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(bp) }).then(j<Artifacts>),
  createBlueprint: (id: string, blueprint: Blueprint) =>
    fetch("/api/blueprints", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ id, blueprint }) }).then(j<{ id: string }>),
  saveBlueprint: (id: string, blueprint: Blueprint) =>
    fetch(`/api/blueprints/${encodeURIComponent(id)}`, { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify(blueprint) }).then(j<{ id: string }>),
  deleteBlueprint: (id: string) =>
    fetch(`/api/blueprints/${encodeURIComponent(id)}`, { method: "DELETE" }).then(j<{ deleted: string }>),
};
