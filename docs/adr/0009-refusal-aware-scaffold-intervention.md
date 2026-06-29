# ADR-0009 — The refusal-aware scaffold intervention

- **Date**: 2026-06-28
- **Status**: Accepted
- **Extends**: ADR-0006 (meridian + the leaderboard protocol), ADR-0008 (factory + holdout)

## Context

The leaderboard (ADR-0006) measures reliability under one fixed prompt; the
`unresolvable` column reads 40/0/0/0/0 — every model but one fabricates a tie-break
rather than refusing. The open question is whether that failure is a property of the
models or partly of how they are *scaffolded* to handle conflict. The task prompt is
already refusal-instructed ("say you do not know rather than guessing"), so a clean
test cannot simply add a refusal instruction; it must contrast that generic nudge with
an explicit, taxonomy-driven refusal procedure, changing nothing else. A second problem
is statistical: a single org realises each conflict type with five probes, too few to
test an intervention. The factory (ADR-0008) is what makes the test powerable.

## Decision

1. **Two scaffolds, one surgical difference.** `tessera_probes` gains a `scaffold`
   parameter selecting two prompts that share intro, reconciliation policy, and answer
   contract verbatim and differ in exactly one block:
   - **`baseline` (B0)** — the published-leaderboard prompt, kept byte-identical, so
     existing det-4/k=3 meridian logs *are* the B0 arm and the delegation producer is
     unchanged.
   - **`refusal_aware` (R1)** — replaces B0's one generic refusal sentence with an
     explicit detect → classify → escalate procedure that turns the four-type taxonomy
     into an action rule (answer none/resolvable; refuse the unresolvable tie and the
     void record rather than invent a resolution).
   A test (`tests/test_task.py`) pins that the two arms differ *only* in that block.

2. **Execution, not discovery.** R1 names the taxonomy and the stakes of refusing, but
   not which probes are ties — the agent still discovers those by reading the silos. The
   study stays within the policy-execution scope of ADR-0006.

3. **Powered, paired design over the factory.** The contrast is run across five
   instances (the authored meridian, seed 0, plus factory seeds 1–4), 110 probe-
   instances per model per arm, paired per `(instance, probe)` on strict pass^3 and
   compared with an exact McNemar test. H1₂'s two clauses — a refusal gain on
   unresolvable/void *without* a significant answering loss on none/resolvable — are
   tested on the two disjoint probe subsets separately, so a gain bought by over-refusal
   is visible rather than netted away.

4. **Holdout confirmation.** The capable-model effect is re-checked on a *withheld*
   factory seed under the ADR-0008 commitment (commit → run → reveal → verify), so the
   gain is not an artifact of instances seen while authoring the scaffold.

## Result (2026-06-28, det-4, k=3, four API models)

The intervention is a **capability amplifier, not a substitute**. R1 significantly
improves correct refusal, without a significant answering loss, for the models that can
perceive the conflict — claude-sonnet-4-6 (refusal subset 18 helped / 1 harmed,
p = 0.0001; net 75.5% → 95.5%) and gpt-4o (9 / 0, p = 0.004). On claude-haiku-4-5 the
refusal gain is real (9 / 1, p = 0.022) but offset by over-refusal on resolvable probes,
so net behaviour is unchanged (p = 0.86). gpt-4o-mini, which fails the cross-silo joins
upstream, never reaches the ties (0 / 0) and H0₂ is retained. The full tables and the
holdout reveal are in [docs/scaffold.md](../scaffold.md).

## Scope / non-goals

Four API models (the open-weights qwen3.5 row is not re-run under both arms); one org
family (`meridian` + four seeds); the deterministic engine only. A refined scaffold that
keeps the refusal gain without the over-refusal cost, and breadth across distinct org
shapes, are future work.

## Consequences

- The intervention promised by the methodology (H0₂/H1₂) is realised, not planned; the
  thesis reports it in Chapter 4 with both prompts in Appendix B.
- Refusal is reframed as capability-conditioned: prompting converts detection into
  refusal but cannot manufacture detection — a result that predicts where the scaffold
  will and will not help before it is tried.
- The factory (ADR-0008) earns its first inferential use: the per-type counts it holds
  fixed are what make the paired McNemar test meaningful.
