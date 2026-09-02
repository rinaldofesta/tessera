import { afterEach, describe, expect, it, vi } from "vitest";
import { api, toSpec, toStatus, toSummary } from "./api";
import type { Run, RunConfig } from "./types";

function run(overrides: Partial<Run> = {}): Run {
  return {
    ok: true,
    id: "run-1",
    status: "completed",
    source: "run",
    archived: false,
    schema_version: 1,
    created_at: "2026-09-02T10:00:00Z",
    started_at: "2026-09-02T10:00:01Z",
    finished_at: "2026-09-02T10:01:00Z",
    request: {
      suite: "meridian", model: "ollama/test", engine: "deterministic",
      grader: null, k: 5, scaffold: "refusal_aware", seed: 4,
    },
    verdict: { pass_k_rate: 0.7, mean_rate: 0.9, label: "inconsistent", sentence: "Not reliable." },
    gate: null,
    report: null,
    receipt: null,
    diagnostics: [],
    paths: { dir: "/runs/run-1", log: null, report_json: null, report_md: null },
    error: null,
    ...overrides,
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("run API adapter", () => {
  it.each([
    ["queued", "running"],
    ["running", "running"],
    ["completed", "done"],
    ["failed", "error"],
    ["interrupted", "error"],
  ] as const)("maps %s to %s", (status, expected) => {
    expect(toSummary(run({ status })).status).toBe(expected);
    expect(toStatus(run({ status })).status).toBe(expected);
  });

  it("maps the ADR-0002 request and verdict into the old summary fields", () => {
    expect(toSummary(run())).toEqual({
      id: "run-1", status: "done", error: null, model: "ollama/test",
      org: "meridian", judge: "deterministic", grader: null, epochs: 5,
      created_at: "2026-09-02T10:00:00Z", finished_at: "2026-09-02T10:01:00Z",
      pass_k_rate: 0.7, mean_rate: 0.9, archived: false,
    });
  });

  it("maps the old launcher configuration into RunSpec", () => {
    const config: RunConfig = {
      model: "ollama/test", judge: "llm", grader: "ollama/grader",
      org: "starter", epochs: 3, scaffold: "baseline", seed: 2,
    };
    expect(toSpec(config)).toEqual({
      model: "ollama/test", engine: "llm", grader: "ollama/grader",
      suite: "starter", k: 3, scaffold: "baseline", seed: 2,
    });
  });

  it("surfaces blocker messages as the existing view error text", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: [
        { code: "not_connected", message: "provider is not connected", fix: "connect" },
        { code: "unknown_suite", message: "suite is unknown", fix: null },
      ],
    }), { status: 422, headers: { "content-type": "application/json" } })));

    await expect(api.startRun({
      model: "openai/test", judge: "deterministic", grader: null,
      org: "missing", epochs: 3, scaffold: "baseline", seed: 0,
    })).rejects.toMatchObject({
      message: "provider is not connected; suite is unknown", status: 422,
    });
  });
});
