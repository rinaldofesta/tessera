# ADR-0013 - Preregister synthetic-to-real rank transfer

- **Date**: 2026-08-23
- **Status**: Accepted
- **Extends**: ADR-0008 (scenario factory and holdout)

## Context

Tessera's public measurements show that its scorer detects cross-silo fabrication. They do
not show that a configuration ranking on a synthetic Meridian-family org predicts a ranking
on private production data.

A post-hoc correlation would be weak evidence. Model membership, harness settings, metric
weights, and generator changes could all be chosen after seeing the result. Mining the same
production eval for generator patterns before measuring transfer would add a second leak: the
synthetic instrument would be fitted to its validation target.

The production candidate is a matching eval built from confidential client material and
personal data. Aggregate publication does not remove the purpose-authorization requirement.

## Decision

1. **Authorization precedes access.** Written purpose approval and an MSA check are required
   before production data is inspected or processed for Tessera. Public attribution requires
   separate written approval.
2. **The call is public before the run.** The exact panel, identities, prompts, hashes,
   scoring formulas, bootstrap seed, and claim language are committed publicly, signed with a
   Git tag, and registered on OSF before the first scored run.
3. **Panel membership is criterion-based.** The intersection contains 7 to 10 unchanged
   single-model configurations, spans at least three providers, includes at least two pinned
   local models, and includes a mid-tier model. Unavailable entries are dropped and disclosed,
   never replaced.
4. **The primary metrics already exist.** Tessera uses strict overall `pass^k`; the production
   suite uses its frozen composite. No new weighted Tessera score is introduced for this study.
5. **The confirmatory gate is one-sided rank transfer.** Kendall's tau-b is bootstrapped over
   tasks after repetitions are collapsed. The lower 95% bound must exceed zero. Effect bands
   bind the public sentence before the run.
6. **Builder diagnostics stay secondary.** Top-three overlap is descriptive. A pair enters
   decisive-pair concordance only when its two-sided 95% score intervals are disjoint on both
   suites; its count and denominator are always published.
7. **`fac-1` stays sealed.** No production-derived fragmentation pattern changes the generator
   before this study. Such patterns may inform `fac-2` afterward and require another holdout.

The complete executable contract lives in
[`docs/validation-preregistration.md`](../validation-preregistration.md). Its `DRAFT` state
blocks runs until the panel, hashes, signed tag, and OSF record are filled.

## Consequences

- A positive result supports transfer in one matching domain, not universal validity.
- A negative or inconclusive result is still published.
- Fewer than 7 or more than 10 eligible configurations stop the study and require a new public
  registration.
- The repository can ship the analyzer before it contains any production data.
- Denied authorization moves the public validation to a design partner; it does not weaken the
  data boundary.
