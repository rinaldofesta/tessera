# ADR-0008 — The scenario-factory and the holdout protocol

- **Date**: 2026-06-19
- **Status**: Accepted
- **Extends**: ADR-0006 (meridian + the leaderboard protocol)

## Context

The public `meridian` blueprint is the answer key, so a contaminated model can
reproduce answers — and, worse, memorize *which questions to refuse*, the leak
that lands on the `unresolvable` column (the headline finding). ADR-0006 named
seeded value-rotation variants as the planned mitigation; this ADR specifies them.

## Decision

1. **The factory is the public artifact.** `tessera.factory.generate_variant(seed)`
   deterministically produces a `meridian`-family blueprint. The family — not a
   single fixed key — is what we publish. It re-deals the conflict graph per seed
   (which answerable slot is `unresolvable` vs `resolvable`, which fields are
   `void`) and synthesizes fresh anti-prior values, holding the meridian category
   counts fixed.

2. **`seed = 0` is canonical and equals the authored meridian.**
   `generate_variant(0)` returns `build_meridian_blueprint()` object-for-object, so
   the published Sonnet 86.4% baseline stays valid. Re-baselining canonical is a
   non-goal.

3. **Holdout rule.** A leaderboard's headline numbers are produced on a *withheld*
   seed. Before the run, the row records a **salted commitment** to the seed, not
   the seed:
   `commitment = SHA-256( factory_version || 0x00 || ascii(seed) || 0x00 || salt )`,
   `salt = os.urandom(32)` (hex). The salt provides hiding — a saltless hash of a
   small integer seed is trivially brute-forced. `tessera.factory.commit` ships
   `commit`/`verify` helpers.

4. **Verify-on-reveal.** Publishing `{seed, salt, factory_version}` lets anyone
   recompute the digest and run `generate_variant(seed)` under that
   `factory_version` to reproduce the exact org and answer key. Determinism is what
   makes withholding safe.

5. **Comparability.** A leaderboard row is comparable within `scorer_version` +
   org-family (`meridian`) + `factory_version` + `k`. `factory_version` is a
   hand-bumped string (`"fac-1"`), bumped when the schema, pools, lexicon, or
   constructors change generated orgs. The pre-factory published rows carry
   `factory_version = "fac-1"/canonical` (the instance `generate_variant(0)`
   produces), so they stay comparable to future canonical-seed rows.

## Scope (v1)

Machinery + this ADR: the generator, the property-test validator, seed addressing
(`-T org=meridian -T seed=K`), the `tessera-variant` export CLI, and the
`commit`/`verify` helpers — all key-free and tested. **Out of scope:** the live
holdout leaderboard run; wiring `factory_version` into `Score.metadata ->
RunHeader -> leaderboard row` and extending `leaderboard._require_uniform` to
include it (deferred with the live runs); a `seed` parameter on the API/UI.

## Known trade-offs

- The 6 `none` chains are a fixed partition (`C(6,6)=1`); acceptable because `none`
  probes answer and require a real cross-silo join.
- `void` rote-refusal is not fully closed (closing it would trade away void
  realism). `void` is not the discriminating column — every published model already
  aces it — so the residual does not affect the headline finding.

## Consequences

- The leaderboard can cite a contamination-resistant, withheld-seed number while
  staying fully reproducible on reveal.
- Meridian's baseline and offline gates survive untouched.
- A new comparability dimension (`factory_version`) is defined now and stamped on
  export; its leaderboard plumbing lands with the live-holdout follow-up.
