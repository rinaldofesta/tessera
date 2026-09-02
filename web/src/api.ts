import { toLegacyStatus } from "@/lib/runStatus";
import type {
  Artifacts, Blueprint, BlueprintMeta, ComparisonIntervention, ComparisonResult, EvalSetup,
  Provider, ProviderUpdate, RescanResult, Run, RunConfig, RunSpec, RunStatus, RunSummary,
  StartRunResult, ValidationResult,
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

export function toSummary(run: Run): RunSummary {
  return {
    id: run.id,
    status: toLegacyStatus(run.status),
    error: run.error,
    model: run.request.model,
    org: run.request.suite,
    judge: run.request.engine,
    grader: run.request.grader,
    epochs: run.request.k,
    created_at: run.created_at,
    finished_at: run.finished_at,
    pass_k_rate: run.verdict?.pass_k_rate ?? null,
    mean_rate: run.verdict?.mean_rate ?? null,
    archived: run.archived,
  };
}

export function toStatus(run: Run): RunStatus {
  return {
    status: toLegacyStatus(run.status),
    report: run.report,
    error: run.error,
  };
}

export function toSpec(cfg: RunConfig): RunSpec {
  return {
    model: cfg.model,
    engine: cfg.judge,
    grader: cfg.grader,
    suite: cfg.org,
    k: cfg.epochs,
    scaffold: cfg.scaffold,
    seed: cfg.seed,
  };
}

export const api = {
  compareRuns: (a: string, b: string, intervention: ComparisonIntervention) =>
    fetch("/api/comparisons", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ a, b, intervention }),
    }).then(j<ComparisonResult>),

  // orgs + models + runs
  listOrgs: () => fetch("/api/orgs").then(j<string[]>),
  listModels: () => fetch("/api/models").then(j<string[]>),
  evalSetup: () => fetch("/api/eval-setup").then(j<EvalSetup>),
  listProviders: () => fetch("/api/providers").then(j<Provider[]>),
  saveProvider: (id: string, body: ProviderUpdate) =>
    fetch(`/api/providers/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<Provider>),
  rescan: () =>
    fetch("/api/model-discovery/rescan", { method: "POST" }).then(j<RescanResult>),
  startRun: (cfg: RunConfig) =>
    fetch("/api/runs", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(toSpec(cfg)),
    }).then(j<Run>).then((run): StartRunResult => ({
      job_id: run.id, status: toSummary(run).status,
    })),
  getRun: (id: string) =>
    fetch(`/api/runs/${encodeURIComponent(id)}`).then(j<Run>).then(toStatus),
  // EventSource isn't fetch-shaped, but network access still routes through this module.
  watchRun: (id: string) => new EventSource(`/api/runs/${id}/events`),
  listRuns: (includeArchived = false) =>
    fetch(`/api/runs${includeArchived ? "?include_archived=true" : ""}`)
      .then(j<Run[]>).then((runs) => runs.map(toSummary)),
  setRunArchived: (id: string, archived: boolean) =>
    fetch(`/api/runs/${encodeURIComponent(id)}/archive`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ archived }),
    }).then(j<Run>).then(toSummary),
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
