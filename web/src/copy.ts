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
    compare: "Compare",
    experiments: "Experiments",
    suites: "Test suites",
    providers: "Providers",
    leaderboard: "Leaderboard",
  },
  apiConnected: "API connected",
  apiDisconnected: "API disconnected",
  apiOriginHint: "The backend this app is talking to",
  shortcuts: "Keyboard: 1–6 switch views",
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

// ----- redesign PR3: compare view -----

/** Persistent per-selection colors — assigned by selection order, max 8 selections. */
export const COMPARE_PALETTE = [
  "#8b93ff", "#4ade80", "#fbbf24", "#f87171",
  "#67e8f9", "#f9a8d4", "#fb923c", "#a3e635",
] as const;

export const COMPARE_COPY = {
  eyebrow: "Compare",
  title: "Evidence, side by side",
  subtitle:
    "pick up to 8 finished evaluations — each keeps its color while selected. The first pick is the baseline every other run is compared against.",
  tabAdHoc: "ad-hoc",
  tabExperiments: "experiments",
  rail: "evaluations",
  railEmpty: "no evaluations indexed yet — finished runs appear here automatically",
  interventions: {
    model: "model",
    scaffold: "scaffold",
    harness: "harness",
    grader: "grader",
    engine: "scoring engine",
    org: "test suite",
    seed: "dataset seed",
    k: "repeat count",
  },
  maxSelected: (n: number) => `up to ${n} selections`,
  baselineTag: "baseline",
  challengerTag: "challenger",
  intervention: "intended change",
  needTwo: "select at least two evaluations to compare",
  controlled: "Controlled comparison",
  controlledDetail: (intervention: string, changed: string) =>
    `intended change: ${intervention}. Changed: ${changed || "nothing"} — no undeclared drift.`,
  drift: "Protocol drift detected",
  driftDetail: (challenger: string, dims: string) => `${challenger}: unexpected ${dims}`,
  gapPanel: "the gap",
  gapPanelSub: "mean − pass^k, in percentage points",
  metricTabs: {
    reliability: "reliability",
    average: "average",
    accuracy: "accuracy",
    provenance: "provenance",
    refusal: "refusal",
  },
  metricByCategory: "by question type",
  metricOverall: "overall, per evaluation",
  significance: "paired outcomes — probe × repeat",
  significanceCols: {
    category: "question type",
    matched: "paired n",
    aWins: "baseline only passes",
    bWins: "challenger only passes",
    p: "exact p",
  },
  unmatched: (n: number, list: string) => `${n} unmatched observation(s): ${list}`,
  importButton: "Import .eval",
  importHint: "inspect once, then explicitly add it to the evaluation library",
  importInspecting: (name: string) => `local — ${name}`,
  importAdd: "add to library",
  importAdding: "adding…",
  importClose: "close",
  importFailed: (detail: string) => `upload failed: ${detail}`,
  detail: "receipt & diagnostics",
  protocolFingerprint: "protocol fingerprint",
  executionFingerprint: "execution fingerprint",
  effectiveModel: "effective model",
  notReported: "not reported",
  duration: (s: string) => `${s}s`,
  durationLabel: "duration",
  billedCost: "billed cost",
  runtime: "runtime",
  tokensUsed: "tokens used",
  signatures: "failure signatures",
  noSignatures: "no recorded failure signatures",
  frictionTitle: (arm: string, model: string) => `${arm} friction — ${model}`,
  forkExperiment: "fork as controlled experiment",
  exportHtml: "Export HTML",
  exportJson: "Export JSON",
  exportTitle: (evaluations: number) => `tessera — comparison of ${evaluations} evaluations`,
  exportHeading: "tessera — comparison",
  pairHeading: (challenger: string) => `baseline vs ${challenger}`,
  exportFailed: (detail: string) => `export failed: ${detail}`,
  loadFailed: (what: string, detail: string) => `${what}: ${detail}`,
} as const;

export const engineLabel = (engine: string) =>
  engine === "llm" ? "ai grader" : engine === "deterministic" ? "fixed rules" : engine;

/** Display names for the built-in suites. A custom suite falls back to its id, which is
 *  the name its author gave it. */
export const DATASET_LABELS: Record<string, string> = {
  toy: "Toy starter",
  meridian: "Meridian",
  your: "Your organization",
};

export const DATASET_DESCRIPTIONS: Record<string, string> = {
  toy: "tiny 2-account starter — the fastest way to see a full run",
  meridian: "the 22-question benchmark behind the public leaderboard",
  your: "template — copy it to describe your own organization",
};

export const LAUNCHER_COPY = {
  customModel: "custom model…",
  discoveryTitle: "model discovery",
  discoveryLoading: "checking cached model status…",
  discoveryHealthy: "all model sources are available",
  discoveryUnavailable: (detail: string) => `model discovery unavailable: ${detail}`,
  sourceStatus: (source: string, detail: string) => `${source}: ${detail}`,
  rescan: "rescan",
  rescanning: "rescanning…",
  rescanFailed: (detail: string) => `rescan failed: ${detail}`,
  curatedGroup: "curated — published leaderboard set",
  discoveredGroup: "discovered — available beyond the curated set",
  missingConfiguration: (envVars: string[]) =>
    envVars.length > 0 ? `missing ${envVars.join(", ")}` : "configuration missing",
  awaitingRescan: "configuration stored — rescan to verify",
  noServer: "no server running",
  runtimeUnreachable: "runtime unreachable",
  unchecked: "unchecked",
  underTest: "under test",
  providersTitle: "provider configuration",
  providersIntro: "Store missing provider settings here. Values are never shown again.",
  providersUnavailable: (detail: string) => `provider configuration unavailable: ${detail}`,
  configuredField: "already stored — leave blank to keep it",
  missingField: "enter a value",
  saveProvider: "store configuration",
  savingProvider: "storing…",
  providerSaved: (provider: string) =>
    `${provider}: value stored but unverified — Rescan confirms reachability.`,
  providerSaveFailed: (detail: string) => `couldn't store configuration: ${detail}`,
} as const;

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

// ---- launcher rework: the guided three-step flow -----------------------------------

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

export const WIZARD_COPY = {
  step1: "Choose a suite",
  step2: "Choose the model",
  step3: "Confirm & launch",
  q1: "What should we test?",
  q1sub: "Pick the set of questions the model will be asked.",
  q2: "Which model are we testing?",
  q2sub: "Only models something has actually confirmed are listed.",
  q3: "Ready to run",
  continueToModel: "Continue — choose the model",
  continueToConfirm: "Continue — confirm & launch",
  launch: "Run evaluation",
  back: "Back",
  cancel: "Cancel",
  suiteMeta: (questions: number, kind: string) =>
    `${questions} question${questions === 1 ? "" : "s"} · ${kind}`,
};

export const MODEL_COPY = {
  publishedGroup: "Published benchmark set — models with a leaderboard run",
  providerGroup: "Available from your providers",
  machineGroup: "On this machine",
  filterPlaceholder: "Filter models…",
  noMatch: "No model matches that filter.",
  retired: "retired",
  ready: "ready",
  unchecked: "unchecked",
  hiddenCount: (n: number) => `${n} hidden`,
  hiddenWhy: "Models whose provider isn't set up, or whose runtime isn't running, aren't listed.",
  addProvider: "Add a provider →",
  rescan: "Rescan",
  rescanning: "Rescanning…",
  localGroup: "On this machine — not currently running",
  needsServer: "on disk, no server",
  runtimeOffline: "runtime not running",
  copyCommand: "Copy start command",
  copied: "Command copied",
  customRow: "Use a custom model ID…",
  customPlaceholder: "provider/model — e.g. openrouter/meta-llama/llama-4-maverick",
  customHint: "Any model string inspect_ai accepts. Its provider's key must be configured.",
};

export const CONFIRM_COPY = {
  summary: (questions: number, repeats: number, judge: string) =>
    `${questions} question${questions === 1 ? "" : "s"}, asked ${repeats} time${repeats === 1 ? "" : "s"} each, graded by ${judge === "llm" ? "a second model" : "fixed rules"}.`,
  suite: "Test suite",
  model: "Model under test",
  grading: "Grading",
  repeats: "Repeats",
  repeatsValue: (n: number) => `${n} · one wrong repeat fails the question`,
  deterministic: "fixed rules — no second model needed",
  llm: "ai grader — a second model marks the answers",
  advanced: "Advanced settings — grading, repeats, grader model",
  gradingLabel: "Grading engine",
  graderLabel: "Grader model",
  graderPlaceholder: "Choose a grader",
  graderRequired: "The ai grader needs a second model to mark the answers.",
  selfGrading: "The grader must differ from the model under test — a model can't grade itself.",
  underTestSuffix: " (under test)",
  repeatsLabel: "Repeats",
  repeatsHint: "Each question is asked this many times; one wrong repeat fails it (strict pass^k).",
  launching: "Starting…",
};

/** Provider display names. The API returns registry ids ("openai", "xai"); these are
 *  how the companies write themselves. An unknown id falls back to the id. */
export const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  openrouter: "OpenRouter",
  google: "Google",
  groq: "Groq",
  mistral: "Mistral",
  xai: "xAI",
  mlx: "MLX (local server)",
  ollama: "Ollama",
};

export const PROVIDER_COPY = {
  title: "Providers",
  subtitle: "Keys are written to your local .env and never shown again.",
  configuredGroup: "Configured",
  notConfiguredGroup: "Not configured",
  configured: "configured",
  notConfigured: "not set",
  add: "Add key",
  replace: "Replace",
  save: "Save",
  saving: "Saving…",
  saved: (provider: string) => `${provider} key stored`,
  savedHint: "Stored, not yet verified — Rescan on the model step confirms what it reaches.",
  saveFailed: "Couldn't store that key",
  keyPlaceholder: "paste the key",
  urlPlaceholder: "http://localhost:8080/v1",
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
  compareSelected: "Compare selected →",
} as const;

export const DASHBOARD_COPY = {
  eyebrow: "Home",
  title: "The reliability program at a glance",
  subtitle: "latest score, the gap over time, and recent runs",
  latestReliability: "latest reliability",
  latestAverage: "latest average",
  averageSubtitle: "success rate",
  runsTotal: "runs total",
  completed: "completed",
  errored: (n: number) => `${n} errored`,
  noCompleted: "no completed runs",
  trendTitle: "the gap over time",
  trendSubtitle: "pass^k vs mean per run, oldest → newest — the amber band is the fragility",
  legendReliability: "reliability (pass^k)",
  legendAverage: "average success rate",
  emptyTitle: "no runs recorded yet",
  emptyBody: "history and trends appear after the first live eval",
  emptyCta: "Run the first eval",
  recentTitle: (shown: number, total: number) =>
    total > shown ? `recent runs (${shown} of ${total})` : `recent runs (${total})`,
  openRuns: "open run history →",
} as const;

export const LEADERBOARD_COPY = {
  eyebrow: "Leaderboard",
  title: "Public reliability results",
  subtitle:
    "generated from the committed manifest — the repo file is the source of truth, this view just renders it",
  protocol: (org: string, k: number, scorer: string) => `${org} · pass^${k} · scorer ${scorer}`,
  scaffoldTag: (s: string) => `scaffold: ${s}`,
  seedTag: (n: number) => `seed ${n}`,
  harnessTag: (h: string) => `harness: ${h}`,
  canonical: "View the canonical markdown",
  empty: "the manifest has no rows yet",
  loadFailed: (detail: string) => `couldn't load the leaderboard: ${detail}`,
} as const;

export const EXPERIMENTS_COPY = {
  error: (detail: string) => detail,
  defaultName: "model contrast",
  createTitle: "new controlled experiment",
  preflightUnchecked: "not checked",
  preflightReady: (model: string | null | undefined) => `ready · ${model ?? "identity unreported"}`,
  experimentName: "experiment name",
  testSuite: "test suite",
  intendedChange: "one intended change",
  model: "model",
  refusalScaffold: "refusal scaffold",
  baselineModel: "baseline model",
  modelUnderTest: "model under test",
  challengerModel: "challenger model",
  paidCheck: "paid capability check",
  checking: "checking…",
  repeats: "independent run repeats",
  costCeiling: "cost ceiling (optional USD)",
  noCeiling: "no ceiling",
  checkHint: "capability checks are optional and make a small paid call; listing a model alone does not prove tool support",
  starting: "starting…",
  runCells: (n: number) => `run ${n} cells`,
  experiments: (n: number) => `experiments (${n})`,
  cells: (done: number, total: number) => `${done}/${total} cells`,
  costUnknown: "cost unknown",
  noExperiments: "no experiments yet",
  matrix: (name: string) => `matrix — ${name}`,
  resume: "resume missing cells",
  compare: "compare with baseline",
  status: "status",
  cellCount: "cells",
  cost: "cost",
  unknown: "unknown",
  baseline: "baseline",
  noBaseline: "—",
  pairedResult: "paired experiment result",
  pairedObservations: "paired observations",
  baselineOnly: "baseline only passes",
  challengerOnly: "challenger only passes",
  exactP: "exact p",
  pairedRepeats: (repeats: number[], dimensions: string[]) =>
    `paired independent repeats: ${repeats.join(", ")}; changed dimensions: ${dimensions.join(", ")}`,
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
