import type {
  Artifacts, Blueprint, BlueprintMeta, EvalSetup, LogMeta, Provider, ProviderUpdate,
  RescanResult, Report, RunConfig, RunStatus, RunSummary, StartRunResult, TrendPoint,
  ValidationResult,
} from "./types";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), res.status, detail);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(message: string, public status: number, public detail: unknown) {
    super(message);
  }
}

export const api = {
  // logs / reports
  listLogs: () => fetch("/api/logs").then(j<LogMeta[]>),
  getReport: (id: string) => fetch(`/api/logs/${encodeURIComponent(id)}/report`).then(j<Report>),
  uploadReport: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch("/api/reports", { method: "POST", body: fd }).then(j<Report>);
  },

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
    fetch("/api/runs", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(cfg) })
      .then(j<StartRunResult>),
  getRun: (id: string) => fetch(`/api/runs/${encodeURIComponent(id)}`).then(j<RunStatus>),
  // EventSource isn't fetch-shaped, but network access still routes through this module.
  watchRun: (id: string) => new EventSource(`/api/runs/${id}/events`),
  listRuns: () => fetch("/api/runs").then(j<RunSummary[]>),
  trends: (q: { org?: string; model?: string; engine?: string } = {}) => {
    const p = new URLSearchParams(Object.entries(q).filter(([, v]) => v) as [string, string][]);
    return fetch(`/api/trends?${p}`).then(j<TrendPoint[]>);
  },

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
