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

export const MONITOR_COPY = {
  runningTitle: "Evaluation in progress",
  doneTitle: (model: string) => `Evaluated ${model}`,
  status: { running: "running", done: "done", error: "failed" } as Record<string, string>,
  elapsed: (t: string) => `Running for ${t}`,
  model: "Model",
  suite: "Suite",
  grading: "Grading",
  safeToLeave: "Safe to leave this page — the run continues on the server. You'll find it under Runs.",
  failed: "The run failed",
  allRuns: "All runs",
  newRun: "New evaluation",
  exportHtml: "Export HTML",
  exportJson: "Export JSON",
  exportFailed: "couldn't export the report",
};

// ----- redesign PR1: lifecycle vs verdict vocabularies, gap bar, run history -----

/** Lifecycle only. "finished" is neutral on purpose — completion says nothing
 *  about reliability; VerdictBadge speaks to that. */
export const STATUS_COPY = {
  running: "running…",
  done: "finished",
  error: "failed",
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
} as const;

export const RUN_HISTORY_COPY = {
  eyebrow: "Run history",
  title: "Every evaluation you've launched",
  subtitle:
    "raw runs — live, finished, and errored. The gap bar reads: solid = reliable every repeat, hatched = passes only sometimes.",
  filterPlaceholder: "filter by model, suite, or grader…",
  statusAll: "all statuses",
  suiteAll: "all suites",
  showing: (shown: number, total: number) =>
    shown === total ? `${total} runs` : `${shown} of ${total} runs`,
  empty: "no runs yet — launch the first evaluation to start the history",
  emptyCta: "New evaluation",
  details: "Details",
  rerun: "Rerun",
  meta: (org: string, grading: string, k: number) => `${org} · ${grading} · ${k} repeats`,
  noScore: "—",
  selectRun: (model: string) => `select ${model} for comparison`,
  exportHtml: "HTML",
  exportJson: "JSON",
  exportFailed: "couldn't load the report for export",
  archive: "Archive",
  unarchive: "Unarchive",
  archivedBadge: "archived",
  showArchived: "show archived",
  archiveFailed: "couldn't change the archive flag",
} as const;

// ----- redesign PR2: scorecard + export vocabulary -----

export const SCORECARD_COPY = {
  gradedBy: (engine: string, grader: string | null) =>
    engine === "llm"
      ? `scored by an ai grader${grader ? ` (${grader})` : ""}`
      : "scored by fixed rules",
  protocol: (questions: number, k: number) => `${questions} questions × ${k} repeats`,
  scorer: (v: string | null) => (v ? `scorer ${v}` : "scorer version not recorded"),
  seed: (s: number) => `dataset variant seed ${s}`,
  scaffold: (s: string) => `prompt scaffold: ${s}`,
  harness: (h: string) => `harness: ${h} (how model calls were dispatched)`,
  reliableVerdict: (k: number) => `Reliable — correct behavior in all ${k} repeats of every probe.`,
  notReliableVerdict: (categories: string) =>
    `Not reliable on ${categories} — it does not behave correctly every time; a single average score would hide this.`,
  reliability: "reliability",
  reliabilitySub: (k: number) => `passed all ${k} repeats — pass^${k}`,
  average: "average",
  averageSubWithGap: (gapPp: number) => `mean rate across repeats · gap ${gapPp} pp`,
  byCategory: "reliability by question type",
  byAxis: "how it failed, by axis",
  categoryMeta: (key: string, behavior: string, desc: string) => `${key} · expect ${behavior} — ${desc}`,
  categoryLine: (k: number, meanPct: string) => `pass^${k} · mean ${meanPct}`,
  meanShort: (meanPct: string) => `mean ${meanPct}`,
  axisAccuracy: "right answers",
  axisAccuracySub: (n: number) => `accuracy · ${n} answer-epochs`,
  axisProvenance: "cited the right sources",
  axisProvenanceSub: (n: number) => `provenance · ${n} epochs`,
  axisRefusal: "refused when it should",
  axisRefusalSub: (n: number) => `refusal · ${n} refuse-epochs`,
  axisFormat: "answered in the expected format",
  axisFormatSub: "the ANSWER: <value> contract",
  axesNote:
    'denominators differ — an axis only counts where it applies. "cited the right sources" is read from the agent\'s real tool calls, never judged by a model.',
  failures: "failures",
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
