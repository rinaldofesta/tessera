// Shared plain-language vocabulary. The pattern everywhere: plain words first, the
// technical term demoted to a caption/parenthetical — never removed, because the docs
// and the public leaderboard still speak it.

import type { ProbeDef } from "./types";

export const SHELL_COPY = {
  brand: "tessera",
  newEvaluation: "New evaluation",
  navLabel: "Primary navigation",
  navItems: {
    home: "Home",
    runs: "Runs",
    suites: "Test suites",
    leaderboard: "Leaderboard",
  },
  apiConnected: "API connected",
  apiDisconnected: "API disconnected",
  apiOriginHint: "The API answers on this origin",
  shortcuts: "Keyboard: 1–4 switch views",
  help: "Help & docs",
} as const;

export const CONFLICT: Record<string, { label: string; behavior: "answer" | "refuse"; desc: string }> = {
  none: {
    label: "sources agree",
    behavior: "answer",
    desc: "facts agree across sources — stitch them into one answer",
  },
  resolvable: {
    label: "conflict, tiebreaker applies",
    behavior: "answer",
    desc: "sources clash but a rule (newer / more authoritative) breaks the tie",
  },
  unresolvable: {
    label: "genuine disagreement",
    behavior: "refuse",
    desc: "equal-authority sources clash, no tiebreaker — must refuse and escalate",
  },
  void: {
    label: "fact missing",
    behavior: "refuse",
    desc: "the fact is absent — must refuse, not invent it",
  },
};

export const conflictLabel = (key: string) => CONFLICT[key]?.label ?? key;

export const engineLabel = (engine: string) =>
  engine === "llm" ? "ai grader" : engine === "deterministic" ? "fixed rules" : engine;

export const DATASET_DESCRIPTIONS: Record<string, string> = {
  toy: "tiny 2-account starter — the fastest way to see a full run",
  meridian: "the 22-question benchmark behind the public leaderboard",
  your: "template — copy it to describe your own organization",
};

// The scenario wizard's 5 authoring recipes (docs/tessera-lesson.html, module 5).
// expected_behavior is never asked in the wizard — it's derived from CONFLICT[...].behavior.
export type RecipeKey = "agree" | "recency" | "authority" | "disagreement" | "void";

export const RECIPE_CONFLICT: Record<RecipeKey, ProbeDef["conflict_type"]> = {
  agree: "none",
  recency: "resolvable",
  authority: "resolvable",
  disagreement: "unresolvable",
  void: "void",
};

export const RECIPES: Record<RecipeKey, { title: string; blurb: string; example: string }> = {
  agree: {
    title: "sources agree",
    blurb: "two sources describe the same thing with no conflict — the agent should stitch them into one answer.",
    example: "a crm tier field points to a docs page that spells out what the tier means.",
  },
  recency: {
    title: "conflict, newer wins",
    blurb: "an old value and a newer one disagree — the newer one should win.",
    example: "a stale crm renewal date vs. a fresher note from the account team.",
  },
  authority: {
    title: "conflict, more official wins",
    blurb: "two values disagree, but one source clearly outranks the other.",
    example: "a signed contract clause overrides a casual mention elsewhere.",
  },
  disagreement: {
    title: "genuine disagreement",
    blurb: "two equally trustworthy sources clash with no tiebreaker — the agent must refuse and escalate.",
    example: "the crm and the deal desk quote different contract values, same authority, same date.",
  },
  void: {
    title: "fact missing",
    blurb: "nobody ever recorded this — the agent must say so, not invent an answer.",
    example: "a subject with no billing address on file anywhere.",
  },
};
