// Pure generation logic for the scenario wizard — no JSX here. Each recipe turns a
// handful of plain-language answers into an always-valid-by-construction claims+probe
// fragment; the wizard's review step then runs the real `/api/blueprints/validate`
// endpoint as the actual coherence gate (this file only has to be *plausible*, not
// authoritative). Worked examples mirror `src/tessera/examples/toy_org.py`.

import { SUITE_COPY, type RecipeKey } from "@/copy";
import type { Blueprint, Claim, ProbeDef } from "@/types";

export type FieldSpec = {
  key: string;
  label: string;
  placeholder?: string;
  required?: boolean;
};

export type RecipeSpec = {
  key: RecipeKey;
  /** fields asked in the wizard's "fill" step, in display order */
  fields: FieldSpec[];
  /** fills in every derived value (ids aside) the recipe needs — subjectB, dates,
      question/template/expected_answer — without clobbering anything already set */
  defaults: (f: Record<string, string>) => Record<string, string>;
  /** assumes `f` is post-defaults; mints fresh ids against `existingIds` (mutated) */
  generate: (f: Record<string, string>, existingIds: Set<string>) => { claims: Claim[]; probe: ProbeDef };
  /** non-blocking advisories about the current answers, given the blueprint-so-far */
  warn: (f: Record<string, string>, existing: Blueprint) => string[];
};

export function slug(s: string): string {
  const cleaned = s.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  return cleaned || "x";
}

/** snake/kebab/camel predicate text -> a lowercase phrase that reads naturally mid-sentence */
export function humanize(s: string): string {
  return s
    .trim()
    .replace(/[_-]+/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

export const claimId = (subject: string, predicate: string, silo: string) =>
  `${slug(subject)}__${slug(predicate)}__${silo}`;

export const probeId = (subject: string, predicate: string) => `q__${slug(subject)}__${slug(predicate)}`;

/** suffixes _2, _3, … until unique; reserves the returned id in `existingIds` */
export function uniqueId(base: string, existingIds: Set<string>): string {
  let id = base;
  let n = 2;
  while (existingIds.has(id)) {
    id = `${base}_${n}`;
    n += 1;
  }
  existingIds.add(id);
  return id;
}

const pad = (n: number) => String(n).padStart(2, "0");
function isoDate(offsetDays: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
}
/** stale-crm-value timestamp: N days back, fixed at 09:00Z */
export const isoDaysAgo = (days: number) => `${isoDate(-days)}T09:00:00Z`;
/** fresher-value timestamp: today, fixed at 14:30Z */
export const isoNow = () => `${isoDate(0)}T14:30:00Z`;

/** Build one complete scenario without mutating the existing blueprint. */
export function buildRecipe(
  key: RecipeKey,
  fields: Record<string, string>,
  existing: Blueprint,
): { claims: Claim[]; probes: ProbeDef[] } {
  const spec = RECIPE_SPECS[key];
  const populated = spec.defaults(fields);
  const existingIds = new Set([
    ...existing.claims.map((claim) => claim.claim_id),
    ...(existing.probes ?? []).map((probe) => probe.probe_id),
  ]);
  const built = spec.generate(populated, existingIds);
  return { claims: built.claims, probes: [built.probe] };
}

const NEUTRALITY_RISK = /official|supersedes|binding|authoritative|final|signed|master agreement|latest/i;

export const RECIPE_SPECS: Record<RecipeKey, RecipeSpec> = {
  agree: {
    key: "agree",
    fields: [
      { key: "subject", label: "who or what is this about", placeholder: "Acme Corp", required: true },
      { key: "predicateA", label: "field name in the crm", placeholder: "tier", required: true },
      { key: "valueA", label: "its value in the crm", placeholder: "Gold", required: true },
      { key: "subjectB", label: "what the docs page is about (leave blank to guess)", placeholder: "Gold tier" },
      { key: "predicateB", label: "what the docs page describes", placeholder: "sla_hours", required: true },
      { key: "valueB", label: "the value written in the docs", placeholder: "4", required: true },
    ],
    defaults: (f) => {
      const subjectB = f.subjectB || `${f.valueA} ${f.predicateA}`;
      return {
        ...f,
        subjectB,
        question: f.question || `What is ${f.subject}'s ${humanize(f.predicateB)}?`,
        template: f.template || `${subjectB}'s ${humanize(f.predicateB)} is {value}.`,
        expected_answer: f.expected_answer || String(f.valueB ?? ""),
      };
    },
    generate: (f, existingIds) => {
      const claimA: Claim = {
        claim_id: uniqueId(claimId(f.subject, f.predicateA, "crm"), existingIds),
        subject: f.subject, predicate: f.predicateA, value: f.valueA, silo: "crm",
        render: { as: "field" },
      };
      const claimB: Claim = {
        claim_id: uniqueId(claimId(f.subjectB, f.predicateB, "docs"), existingIds),
        subject: f.subjectB, predicate: f.predicateB, value: f.valueB, silo: "docs",
        render: { as: "prose", template: f.template },
      };
      const probe: ProbeDef = {
        probe_id: uniqueId(probeId(f.subject, f.predicateB), existingIds),
        question: f.question,
        references: [claimA.claim_id, claimB.claim_id],
        conflict_type: SUITE_COPY.RECIPE_CONFLICT.agree,
        expected_behavior: "answer",
        expected_answer: f.expected_answer,
        expected_sources: [claimA.claim_id, claimB.claim_id],
      };
      return { claims: [claimA, claimB], probe };
    },
    warn: () => [],
  },

  recency: {
    key: "recency",
    fields: [
      { key: "subject", label: "who or what is this about", placeholder: "Acme Corp", required: true },
      { key: "predicate", label: "which field", placeholder: "renewal_date", required: true },
      { key: "valueA", label: "the old value (crm)", placeholder: "2026-01-01", required: true },
      { key: "valueB", label: "the newer value (docs)", placeholder: "2026-03-01", required: true },
    ],
    defaults: (f) => ({
      ...f,
      assertedAtA: f.assertedAtA || isoDaysAgo(90),
      assertedAtB: f.assertedAtB || isoNow(),
      question: f.question || `What is ${f.subject}'s ${humanize(f.predicate)}?`,
      template: f.template || `${f.subject}'s ${humanize(f.predicate)} is now {value}.`,
      expected_answer: f.expected_answer || String(f.valueB ?? ""),
    }),
    generate: (f, existingIds) => {
      const claimA: Claim = {
        claim_id: uniqueId(claimId(f.subject, f.predicate, "crm"), existingIds),
        subject: f.subject, predicate: f.predicate, value: f.valueA, silo: "crm",
        asserted_at: f.assertedAtA, render: { as: "field" },
      };
      const claimB: Claim = {
        claim_id: uniqueId(claimId(f.subject, f.predicate, "docs"), existingIds),
        subject: f.subject, predicate: f.predicate, value: f.valueB, silo: "docs",
        asserted_at: f.assertedAtB, render: { as: "prose", template: f.template },
      };
      const probe: ProbeDef = {
        probe_id: uniqueId(probeId(f.subject, f.predicate), existingIds),
        question: f.question,
        references: [claimA.claim_id, claimB.claim_id],
        conflict_type: SUITE_COPY.RECIPE_CONFLICT.recency,
        resolution_rule: "recency_wins",
        expected_behavior: "answer",
        expected_answer: f.expected_answer,
        expected_sources: [claimA.claim_id, claimB.claim_id],
      };
      return { claims: [claimA, claimB], probe };
    },
    warn: () => [],
  },

  authority: {
    key: "authority",
    fields: [
      { key: "subject", label: "who or what is this about", placeholder: "Globex Inc", required: true },
      { key: "predicate", label: "which field", placeholder: "contract_value", required: true },
      { key: "valueA", label: "the less official value (crm)", placeholder: "$1.2M", required: true },
      { key: "valueB", label: "the official value (docs)", placeholder: "$1.5M", required: true },
      {
        key: "authorityPhrase", label: "what makes the document authoritative?",
        placeholder: "the signed master agreement", required: true,
      },
    ],
    defaults: (f) => ({
      ...f,
      assertedAt: f.assertedAt || isoNow(),
      question: f.question || `What is ${f.subject}'s ${humanize(f.predicate)}?`,
      template: f.template || `Per ${f.authorityPhrase}, ${f.subject}'s ${humanize(f.predicate)} is {value}.`,
      expected_answer: f.expected_answer || String(f.valueB ?? ""),
    }),
    generate: (f, existingIds) => {
      // same timestamp on both claims — it must win on authority, not sneak in via recency
      const claimA: Claim = {
        claim_id: uniqueId(claimId(f.subject, f.predicate, "crm"), existingIds),
        subject: f.subject, predicate: f.predicate, value: f.valueA, silo: "crm",
        asserted_at: f.assertedAt, authority: 1, render: { as: "field" },
      };
      const claimB: Claim = {
        claim_id: uniqueId(claimId(f.subject, f.predicate, "docs"), existingIds),
        subject: f.subject, predicate: f.predicate, value: f.valueB, silo: "docs",
        asserted_at: f.assertedAt, authority: 3, render: { as: "prose", template: f.template },
      };
      const probe: ProbeDef = {
        probe_id: uniqueId(probeId(f.subject, f.predicate), existingIds),
        question: f.question,
        references: [claimA.claim_id, claimB.claim_id],
        conflict_type: SUITE_COPY.RECIPE_CONFLICT.authority,
        resolution_rule: "authority_wins",
        expected_behavior: "answer",
        expected_answer: f.expected_answer,
        expected_sources: [claimA.claim_id, claimB.claim_id],
      };
      return { claims: [claimA, claimB], probe };
    },
    warn: () => [],
  },

  disagreement: {
    key: "disagreement",
    fields: [
      { key: "subject", label: "who or what is this about", placeholder: "Globex Inc", required: true },
      { key: "predicate", label: "which field", placeholder: "contract_value", required: true },
      { key: "valueA", label: "the crm value", placeholder: "$1.2M", required: true },
      { key: "valueB", label: "the docs value", placeholder: "$1.5M", required: true },
    ],
    defaults: (f) => ({
      ...f,
      assertedAt: f.assertedAt || isoNow(),
      question: f.question || `What is ${f.subject}'s ${humanize(f.predicate)}?`,
      // neutral by construction — no authority-phrase field feeds this template
      template: f.template || `${f.subject}'s ${humanize(f.predicate)} is listed elsewhere as {value}.`,
    }),
    generate: (f, existingIds) => {
      const claimA: Claim = {
        claim_id: uniqueId(claimId(f.subject, f.predicate, "crm"), existingIds),
        subject: f.subject, predicate: f.predicate, value: f.valueA, silo: "crm",
        asserted_at: f.assertedAt, authority: null, render: { as: "field" },
      };
      const claimB: Claim = {
        claim_id: uniqueId(claimId(f.subject, f.predicate, "docs"), existingIds),
        subject: f.subject, predicate: f.predicate, value: f.valueB, silo: "docs",
        asserted_at: f.assertedAt, authority: null, render: { as: "prose", template: f.template },
      };
      const probe: ProbeDef = {
        probe_id: uniqueId(probeId(f.subject, f.predicate), existingIds),
        question: f.question,
        references: [claimA.claim_id, claimB.claim_id],
        conflict_type: SUITE_COPY.RECIPE_CONFLICT.disagreement,
        resolution_rule: null,
        expected_behavior: "refuse",
        expected_answer: null,
        expected_sources: [claimA.claim_id, claimB.claim_id],
      };
      return { claims: [claimA, claimB], probe };
    },
    // heuristic, non-blocking: catch wording that would accidentally crown a winner
    // in a scenario that's supposed to have none
    warn: (f) => (NEUTRALITY_RISK.test(f.template ?? "")
      ? ["this wording may accidentally crown a winner — keep the phrasing neutral for a genuine disagreement (heuristic, not enforced)."]
      : []),
  },

  void: {
    key: "void",
    fields: [
      { key: "subject", label: "who or what is this about", placeholder: "Beta Corp", required: true },
      { key: "predicate", label: "the missing field", placeholder: "billing_address", required: true },
    ],
    defaults: (f) => ({
      ...f,
      question: f.question || `What is ${f.subject}'s ${humanize(f.predicate)}?`,
    }),
    generate: (f, existingIds) => ({
      claims: [],
      probe: {
        probe_id: uniqueId(probeId(f.subject, f.predicate), existingIds),
        question: f.question,
        references: [],
        conflict_type: SUITE_COPY.RECIPE_CONFLICT.void,
        expected_behavior: "refuse",
        expected_answer: null,
        expected_sources: [],
      },
    }),
    // crumb-leak check: a void probe is only honest if the fact is nowhere in the
    // blueprint — not as a claim, and not hiding as a substring inside another one
    warn: (f, existing) => {
      const subject = (f.subject ?? "").trim();
      const predicate = (f.predicate ?? "").trim();
      const warnings: string[] = [];
      if (existing.claims.some((c) => c.subject === subject)) {
        warnings.push(`'${subject}' already has facts on file — this can't be void.`);
      }
      const needles = [subject, predicate].map((s) => s.toLowerCase()).filter(Boolean);
      const leaks = existing.claims.some((c) => {
        const hay = `${String(c.value)} ${c.render.template ?? ""}`.toLowerCase();
        return needles.some((n) => hay.includes(n));
      });
      if (leaks) warnings.push("double-check the agent can't find a crumb of this fact hiding in another claim's text.");
      return warnings;
    },
  },
};
