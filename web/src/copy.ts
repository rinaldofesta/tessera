// Shared plain-language vocabulary. The pattern everywhere: plain words first, the
// technical term demoted to a caption/parenthetical — never removed, because the docs
// and the public leaderboard still speak it.

import type { ProbeDef } from "./types";

export const NAV_COPY = {
  brand: "Tessera",
  label: "primary navigation",
  run: "Run",
  reports: "Reports",
  connect: "Connect a model",
  suites: "Suites",
  howItWorks: "How it works",
  apiConnected: "API connected",
  apiDisconnected: "API disconnected",
} as const;

export const RUN_COPY = {
  ask: "Ask",
  the: "the",
  questions: "questions,",
  timesEach: "times each.",
  modelLabel: "model",
  suiteLabel: "suite",
  repeatsLabel: "times each",
  customModel: "Type a model id…",
  customModelPlaceholder: "provider/model",
  customSuite: "Make your own suite…",
  advanced: "Advanced — grading, grader, scaffold, seed",
  engine: "grading engine",
  deterministic: "deterministic",
  llm: "ai grader",
  grader: "grader model",
  chooseGrader: "choose a grader",
  graderRequired: "Choose a second model to grade the answers.",
  selfGrading: "The grader must differ from the model under test.",
  scaffold: "scaffold",
  seed: "seed",
  run: "Run",
  running: "Starting…",
  note: "about 2 minutes · nothing leaves your machine except the model calls",
  pending: (questions: number, k: number) => `pending · ${questions} questions × ${k} repeats`,
  runAnother: "Run another",
} as const;

export const CONNECT_COPY = {
  title: "Connect a model",
  subtitle: "Credentials stay on this machine and are never shown again.",
  connected: "connected",
  pasteKey: "paste a key",
  url: "URL",
  apiKey: "API key",
  baseUrl: "base URL",
  keyPlaceholder: "paste the key",
  urlPlaceholder: "http://localhost:8080/v1",
  save: "Save",
  saving: "Saving…",
  mlxHint: "Ollama, MLX, vLLM — paste the base URL; models are typed by id",
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

export const MOSAIC_COPY = {
  caption: (questions: number, repeats: number, total: number) =>
    `${total} answers — ${questions} question${questions === 1 ? "" : "s"}, ${repeats} repeat${repeats === 1 ? "" : "s"} each`,
  // Once tiles carry results the grid needs a key, or it is 12 coloured squares
  // meaning nothing to the person reading it.
  resolved: (passed: number, total: number, questions: number, repeats: number) =>
    `${passed} of ${total} answers passed — ${questions} question${questions === 1 ? "" : "s"}, ${repeats} repeat${repeats === 1 ? "" : "s"} each`,
  aria: (questions: number, repeats: number) =>
    `Answer grid: ${questions} questions by ${repeats} repeats`,
};

/** Lifecycle only. "finished" is neutral on purpose — completion says nothing
 *  about reliability; VerdictBadge speaks to that. */
export const STATUS_COPY = {
  queued: "queued…",
  running: "running…",
  completed: "finished",
  failed: "failed",
  interrupted: "interrupted",
} as const;

export const VERDICT_COPY = {
  reliable: "reliable",
  inconsistent: "inconsistent",
  unreliable: "unreliable",
} as const;

export const GAP_COPY = {
  /** Full-sentence aria for the gap bar. Gap is percentage points, never "%" of anything. */
  aria: (passKPct: string, k: number, meanPct: string, gapPp: number) =>
    `${passKPct} reliable (pass^${k}), ${meanPct} mean success, ${gapPp} point gap`,
  headline: (k: number, meanPct: string, gapPp: number) =>
    `pass^${k} · mean ${meanPct} · gap ${gapPp} pp`,
  rightEveryTime: "right every time",
  onlySometimes: "only sometimes",
  never: "never",
} as const;

export const REPORT_COPY = {
  save: "Save report",
  copySummary: "Copy summary",
  compare: "Compare with…",
  runAgain: "Run again",
  exportFailed: "couldn't save the report",
  archive: "Archive",
  restore: "Restore",
  archiveFailed: "couldn't change the archive flag",
  copied: "summary copied",
  copyFailed: "couldn't copy the summary",
  failed: "The run did not complete",
  details: "Details",
  categories: "By question type",
  axes: "Three checks",
  axisAccuracy: "right answers",
  axisAccuracySub: (n: number) => `accuracy · ${n} answer-epochs`,
  axisProvenance: "cited the right sources",
  axisProvenanceSub: (n: number) => `provenance · ${n} epochs`,
  axisRefusal: "refused when it should",
  axisRefusalSub: (n: number) => `refusal · ${n} refuse-epochs`,
  failures: "Failures",
  noFailures: (n: number) => `none — all ${n} probes passed every repeat.`,
  probesPassed: (passed: number, total: number) => `${passed}/${total} passed`,
  question: "Q:",
  expected: "expected:",
  expectRefuse: "refuse and escalate",
  expectAnswer: "answer with sources",
  repeatFailed: (epoch: number, why: string) => `repeat ${epoch} — ${why}`,
  consulted: (sources: string) => `consulted: ${sources}`,
  none: "(none)",
  missing: "missing:",
  whyRefuseMissed: "committed to an answer when it should have refused",
  whyRefusalProvenance: "refused correctly, but missed required sources",
  whyWrongAnswer: "wrong answer",
  whyProvenance: "right answer, but missed required sources",
  whyGeneric: "failed a reliability check",
  receipt: "Receipt",
  scorerVersion: "scorer version",
  scaffold: "scaffold",
  seed: "seed",
  protocolHash: "protocol hash",
  logPath: "log path",
  diagnostics: "Diagnostics",
} as const;

export const REPORTS_COPY = {
  eyebrow: "Saved evaluations",
  title: "Reports",
  subtitle: "Open, export, repeat or archive an evaluation.",
  filterPlaceholder: "Filter by model or suite…",
  showArchived: "show archived",
  empty: "No reports yet.",
  emptyCta: "Run your first",
  open: "Open",
  runAgain: "Run again",
  saveHtml: "Save HTML",
  archive: "Archive",
  restore: "Restore",
  archived: "archived",
  exportFailed: "couldn't save the report",
  archiveFailed: "couldn't change the archive flag",
} as const;

export const COMPARE_COPY = {
  title: "Compare with…",
  choose: "Choose a completed report",
  compatible: "comparable — same scorer, suite, repeats, scaffold and seed",
  incompatible: "protocol differs",
  aWins: "A wins",
  bWins: "B wins",
  bothPass: "both pass",
  bothFail: "both fail",
  mcnemar: "McNemar p",
} as const;

// ----- redesign PR4: launch + live merge -----

export const LIVE_COPY = {
  willRunTitle: "what will run",
  liveTitle: (model: string, suite: string) => `live — ${model} on ${suite}`,
  doneTitle: (model: string) => `finished — ${model}`,
  openDetail: "Open run detail →",
  runAnother: "Run another evaluation",
  reliable: (k: number) => `Reliable — correct behavior in all ${k} repeats of every probe.`,
  notReliable: (categories: string) => `Not reliable on ${categories}.`,
  reliability: "reliability",
  reliabilitySub: (k: number) => `pass^${k}`,
  average: "average",
  averageSub: "mean across repeats",
} as const;
