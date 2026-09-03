// Shared plain-language vocabulary. Plain words lead; protocol terms stay available
// where they help users connect the interface to reports and documentation.

import type { ProbeDef } from "./types";

export const NAV_COPY = {
  brand: "Tessera",
  label: "primary navigation",
  run: "Run",
  reports: "Reports",
  connect: "Connect a model",
  howItWorks: "How it works",
  themeTitle: (theme: "system" | "light" | "dark") => `theme: ${theme} — switch appearance`,
  apiConnected: "API connected",
  apiDisconnected: "API disconnected",
} as const;

// ----- VOCAB: shared conflict, verdict, gap and lifecycle language -----

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

export const VERDICT_COPY = {
  reliable: "reliable",
  inconsistent: "inconsistent",
  unreliable: "unreliable",
} as const;

export const GAP_COPY = {
  aria: (passKPct: string, k: number, meanPct: string, gapPp: number) =>
    `${passKPct} reliable (pass^${k}), ${meanPct} mean success, ${gapPp} point gap`,
  rightEveryTime: "right every time",
  onlySometimes: "only sometimes",
  never: "never",
} as const;

export const STATUS_COPY = {
  queued: "queued…",
  running: "running…",
  completed: "finished",
  failed: "failed",
  interrupted: "interrupted",
} as const;

export const conflictLabel = (key: string) => CONFLICT[key]?.label ?? key;
export const engineLabel = (engine: string) =>
  engine === "llm" ? "ai grader" : engine === "deterministic" ? "fixed rules" : engine;

export const RUN_COPY = {
  ask: "Ask",
  the: "the",
  questions: "questions,",
  timesEach: "times each.",
  modelLabel: "model",
  suiteLabel: "suite",
  repeatsLabel: "times each",
  customModel: "Type a model id…",
  customModelPlaceholder: "anthropic/…, ollama/<tag>, openai-api/mlx/<repo>",
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
  subtitle: "Credentials stay on this machine and are never shown again. Cloud providers need a key; Ollama needs only a running daemon; MLX and other OpenAI-compatible servers need their URL.",
  connected: "connected",
  noKeyNeeded: "no key needed",
  pasteKey: "paste a key",
  url: "URL",
  apiKey: "API key",
  baseUrl: "base URL",
  keyPlaceholder: "paste the key",
  urlPlaceholders: {
    ollama: "http://localhost:11434/v1",
    mlx: "http://localhost:8090/v1",
  } as Partial<Record<string, string>>,
  save: "Save",
  saving: "Saving…",
  hints: {
    ollama: "Runs against http://localhost:11434 by default. Paste a URL only if your Ollama runs elsewhere. Models are typed as ollama/<tag>.",
    mlx: "Start the server (for example mlx_lm.server --model <repo> --port 8090) and paste its base URL. Models are typed as openai-api/mlx/<repo>. vLLM and other OpenAI-compatible servers work the same way.",
  } as Partial<Record<string, string>>,
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

export type RecipeKey = "agree" | "recency" | "authority" | "disagreement" | "void";

const RECIPE_CONFLICT: Record<RecipeKey, ProbeDef["conflict_type"]> = {
  agree: "none",
  recency: "resolvable",
  authority: "resolvable",
  disagreement: "unresolvable",
  void: "void",
};

const RECIPES: Record<RecipeKey, { title: string; blurb: string; example: string }> = {
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

export const SUITE_COPY = {
  title: "Make your own suite",
  description: "Create and manage suites with plain-language conflict recipes.",
  listLabel: "suites",
  newSuite: "New suite",
  manage: "manage suites",
  readOnly: "built-in suite — read only",
  nameLabel: "suite name",
  namePlaceholder: "acme-support",
  nameRequired: "Enter a suite name.",
  nameInvalid: "Start with a letter or digit and use only letters, digits, - or _.",
  nameReserved: "That name is reserved for a built-in suite or alias.",
  nameExists: "A suite with that name already exists.",
  loading: "Loading suite…",
  preview: (questions: number, claims: number, silos: string[]) =>
    `${questions} question${questions === 1 ? "" : "s"} · ${claims} claim${claims === 1 ? "" : "s"} · silos: ${silos.join(", ") || "—"}`,
  save: "Save",
  saving: "Saving…",
  delete: "Delete",
  duplicate: "Duplicate as my suite",
  cancel: "Cancel",
  confirmDelete: "Delete suite",
  deleteTitle: (name: string) => `Delete '${name}'?`,
  deleteDescription: "The suite file will be removed. Existing reports are kept.",
  discardTitle: "Discard unsaved changes?",
  discardDescription: "This suite has edits that haven't been saved. Continuing now discards them.",
  discardConfirm: "Discard changes",
  editAnywhere: "edit it in any editor",
  cards: {
    scenarios: (count: number) => `Scenarios · ${count}`,
    newScenario: "+ new scenario",
    empty: "no scenarios yet — a scenario is one test question plus the facts behind it.",
    answer: (answer: string) => `→ answer: ${answer}`,
    refuse: "→ must refuse",
    noFacts: "(no facts — correctly absent)",
    unusedFacts: (count: number) => `Unused facts · ${count}`,
    missingClaim: (id: string) => `‹missing claim: ${id}›`,
    remove: "✕ remove",
  },
  wizard: {
    pickTitle: "new scenario — pick a situation",
    reviewTitle: "review before inserting",
    back: "back",
    next: "next",
    insert: "insert",
    noFacts: "no facts generated for this scenario — the question stands on its own, unanswerable by design.",
    fact: (index: number, silo: string) => `fact ${index} — ${silo}`,
    asOf: (timestamp: string) => `as of ${timestamp}`,
    sentenceTemplate: "sentence template — {value} is replaced by the value",
    older: "as of (crm, older)",
    newer: "as of (docs, newer)",
    question: "question",
    expectedAnswer: "expected answer",
    mustRefuse: "→ must refuse — no answer to give",
    preflight: "preflight — a real validate call against the full blueprint",
    checking: "checking…",
    valid: "✓ valid",
    requestFailed: "validation request failed — backend unreachable?",
  },
  RECIPE_CONFLICT,
  RECIPES,
} as const;

export const LIVE_COPY = {
  liveTitle: (model: string, suite: string) => `live — ${model} on ${suite}`,
  doneTitle: (model: string) => `finished — ${model}`,
  openDetail: "Open run detail →",
  reliability: "reliability",
  reliabilitySub: (k: number) => `pass^${k}`,
  average: "average",
  averageSub: "mean across repeats",
} as const;

export const MOSAIC_COPY = {
  caption: (questions: number, repeats: number, total: number) =>
    `${total} answers — ${questions} question${questions === 1 ? "" : "s"}, ${repeats} repeat${repeats === 1 ? "" : "s"} each`,
  resolved: (passed: number, total: number, questions: number, repeats: number) =>
    `${passed} of ${total} answers passed — ${questions} question${questions === 1 ? "" : "s"}, ${repeats} repeat${repeats === 1 ? "" : "s"} each`,
  aria: (questions: number, repeats: number) =>
    `Answer grid: ${questions} questions by ${repeats} repeats`,
} as const;
