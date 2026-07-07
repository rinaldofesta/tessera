# ADR-0011 — Harness is a displayed comparability axis, not a guarded one

- **Date**: 2026-07-07
- **Status**: Accepted
- **Extends**: ADR-0006 (meridian + the leaderboard protocol)
- **Refines**: ADR-0010 (the leaderboard is generated from a manifest)

## Context

PR #16 put a Mixture-of-Agents ensemble (`moa/max`) into the leaderboard hidden inside the
model-name string, ranked among single-model rows as if it were one. ADR-0010 fixed the
*hand-edit* failure mode and parked the ensemble in an "Out-of-protocol exhibitions"
section, anticipating that `harness` would later become an **executable guard** — a
uniformity dimension like `scaffold`/`seed`.

On implementation that anticipation was wrong, and this ADR records the correction. The
guarded dimensions — `scorer_version`, `org`, `k`, `scaffold`, `seed` — are exactly the
ones that make two rows measure *different things*: a different answer key, a different
strictness bar, different grading rules, a different prompt intervention. A harness runs
the **identical** benchmark instance; only *how the model calls are dispatched* differs. Two
runs that agree on all five guarded dimensions are comparable no matter the harness. The
PR #16 defect was that the ensemble was **hidden**, not that it was **compared**.

## Decision

`harness` is a **displayed axis that rides on top of the guard**; it never weakens it.

1. **`harness` is declared and carried** through `RunHeader` → `serialize` → the API
   contract, defaulting to `"single"`. `tessera_probes` is itself the single-model harness
   and records no harness arg, so every ordinary log reads `"single"`; an ensemble shim
   records e.g. `"ensemble"` in its task_args and the header picks it up. The canonical
   values are **`single`** and **`ensemble`** (free string, but keep the vocabulary
   controlled — a disclosure column is only useful if it does not splinter into
   `moa`/`MoA`/…).
2. **`harness` is NOT in `_require_uniform`.** The guarded set stays
   `(scorer_version, org, k, scaffold, seed)`. A table may mix harnesses.
3. **The leaderboard shows a `harness` column** — conditionally, only when a non-`single`
   row is present, so a table of lone models is byte-identical to a pre-harness one. The
   scorecard discloses harness the same way (a header annotation, only when non-single).
4. **An ensemble row ranks only because it matched every guarded dimension.** This is the
   load-bearing point: the guard is what *lets* the row in, and the harness column is what
   *labels* how it was run. If a future ensemble shim runs a different scaffold or seed, the
   existing guard rejects it from the ranked table outright — it becomes an out-of-protocol
   exhibition, exactly as a mismatched single-model run would. Harness disclosure and the
   comparability guard are orthogonal, and the guard is never relaxed to admit an ensemble.

## Consequences

- `moa/max` leaves the exhibitions section and rejoins the ranked table (currently #4, at
  81.8%), with `harness = ensemble` disclosed in its own column — and the interesting
  finding it exposes is now legible: the ensemble scored *below* opus-4.8 run alone, so the
  advisory sub-models added noise rather than reliability.
- The "Out-of-protocol exhibitions" section changes meaning: it now holds configurations
  that differ in a **guarded** dimension (a different scorer/org/k/scaffold/seed) and are
  therefore genuinely not comparable — not ensembles, which now rank.
- ADR-0010's expectation that harness would "become an executable guard" is superseded by
  this ADR: harness is a disclosure column, not a guard. The two ADRs are consistent
  otherwise — the manifest remains the source of truth, and the ranked table is still a
  deterministic render enforced by CI.
- Comparing an ensemble against single models is a deliberate stance: the leaderboard ranks
  *configurations* by reliability on an identical benchmark, and already ignores cost across
  single models (a 9.7B local model beside a frontier API model). The harness column keeps
  the resource asymmetry honest without segregating the row.
