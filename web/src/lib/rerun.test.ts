import { describe, expect, it } from "vitest";
import { CUSTOM } from "@/components/launcher/ModelStep";
import type { RunSummary } from "@/types";
import { draftFromRun } from "./rerun";

const run: RunSummary = {
  id: "abc",
  status: "done",
  error: null,
  model: "anthropic/claude-sonnet-4",
  org: "meridian",
  judge: "llm",
  grader: "openai/gpt-5.2",
  epochs: 5,
  created_at: "2026-08-29T14:02:11Z",
  finished_at: "2026-08-29T14:31:40Z",
  pass_k_rate: 0.72,
  mean_rate: 0.94,
};

describe("draftFromRun", () => {
  it("copies the run's config when the model is still known", () => {
    const { draft, customId } = draftFromRun(run, ["anthropic/claude-sonnet-4"]);
    expect(draft).toEqual({
      org: "meridian",
      model: "anthropic/claude-sonnet-4",
      judge: "llm",
      grader: "openai/gpt-5.2",
      epochs: 5,
    });
    expect(customId).toBeNull();
  });

  it("falls back to the custom-model slot when the model is no longer offered", () => {
    const { draft, customId } = draftFromRun(run, ["openai/gpt-5.2"]);
    expect(draft.model).toBe(CUSTOM);
    expect(customId).toBe("anthropic/claude-sonnet-4");
  });

  it("narrows an unexpected judge value to deterministic", () => {
    const { draft } = draftFromRun({ ...run, judge: "unexpected" }, []);
    expect(draft.judge).toBe("deterministic");
  });
});
