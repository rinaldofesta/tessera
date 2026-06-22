# ADR-0006 — Meridian ships as the public reference org; the leaderboard protocol

- **Date**: 2026-06-11
- **Status**: Accepted

## Context

The roadmap's leaderboard needs a dataset designed for measurement. The toy org is
a teaching artifact: with one probe per conflict type, a category rate is really
one probe's behavior. Meridian (`src/tessera/examples/meridian_org.py`) was built
to benchmark spec — 10 accounts, 47 claims, 22 probes with ≥5 per conflict type,
both resolution rules (including authority probes where the binding document is
*older* than the CRM row, so recency actively misleads), anti-prior values, and
CRM records wide enough that per-field provenance (ADR-0005) measures real access.

It shipped through three gates:

1. **Offline gates** (in the test suite, permanently): category resolution,
   authority-inverts-recency, mechanical distractor derivation, verbatim
   materialization of every expected answer, the five void holes, tie symmetry.
2. **Adversarial review** — three independent audits (leakage, scoring-contract,
   semantics) returned zero blockers; their should-fixes landed before baseline
   (plan rename that echoed its own answer, off-grid SLA value, genericized prompt
   examples, anchored committed-line refusal, markdown-tolerant ANSWER lines).
3. **Live gates** — a deterministic baseline and an independent llm cross-check,
   with every 0/k probe adjudicated from its transcripts. The first baseline
   caught a real harness flaw (an agent's wrong field-name guess returned an
   ambiguous `{}`; `crm_lookup` now names `_unknown_fields` + `_available_fields`
   like a real API) — fixed and re-run before accepting numbers.

Baseline (Sonnet 4.6, k=3): **det-4 pass^3 86.4% / mean 90.9%** — none, resolvable
(both authority traps included) and void at 100%, provenance 1.0, ANSWER-format
65/66; the *only* failing category is `unresolvable` (2/5 strict, 0.60 mean,
flaky): fabricated tie-breaks. The llm-2 cross-check (gpt-4o grader) agrees at
category level (72.7% / 84.9%, unresolvable 0/5) — divergence concentrates in
judge strictness on hedged refusals, as designed.

## Decision

1. **Meridian is the benchmark org.** The toy org stays the teaching artifact.
2. **The blueprint is public** — honesty over purity. The blueprint *is* the
   answer key, so contamination is possible; v1 accepts that, states it in the
   methodology, and date-stamps results. Seeded value-rotation variants are the
   scenario-factory's first real job when contamination becomes measurable. (Specified in ADR-0008.)
3. **Leaderboard protocol**: deterministic engine (key-free, reproducible by
   anyone), k=3, strict pass^k headline with mean alongside, the per-category
   table mandatory, `scorer_version` published with every row. The llm engine is
   the published cross-check column where a grader was available.
4. **Scope statement**: the task prompt states the reconciliation policy (binding
   beats recency, recency otherwise, refuse on ties). Tessera scores faithful
   *execution* of a given policy, not policy discovery.

## Consequences

- Reliability claims get statistical footing: a meridian category rate averages
  ≥5 probes, and the headline finding — frontier models fabricate precedence on
  symmetric ties while acing everything else — is now isolated by design.
- Anyone can reproduce a leaderboard row with no grader key.
- Published numbers are comparable only within a `scorer_version`; the scorecard
  surfaces it (header) for exactly this reason.
- Contamination is a known, stated risk of v1 rather than a silent one.
