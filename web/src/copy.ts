// Shared plain-language vocabulary. The pattern everywhere: plain words first, the
// technical term demoted to a caption/parenthetical — never removed, because the docs
// and the public leaderboard still speak it.

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
