# The refusal-aware scaffold — an intervention study

Does *scaffolding* an agent to classify conflicts before it answers make it more
reliable? This is the intervention the thesis frames as H2. The study holds the
organization, the tools, the scorer (`det-4`), and the reconciliation policy fixed, and
varies exactly one thing: how refusal on a conflict is prompted.

- **Baseline (B0).** The agent is given the reconciliation policy (a binding source
  overrides others; otherwise the most recent wins) and a single generic nudge — *"if the
  information is missing or genuinely cannot be resolved, say you do not know rather than
  guessing."* This is the prompt that produced [`docs/leaderboard.md`](leaderboard.md),
  kept byte-identical.
- **Refusal-aware (R1).** The same policy and the same answer contract, with that one
  nudge replaced by an explicit per-question procedure that turns the four-type taxonomy
  into an action rule: gather from every source; if the sources agree or only one speaks,
  answer; if they disagree but one is binding (or, absent authority, the most recent)
  resolve and state the rule; **if they disagree with equal authority and no rule breaks
  the tie, do not invent a tiebreaker — say you cannot determine the answer and escalate**;
  if no source carries the record, say you cannot determine the answer. The scaffold hands
  the model the *procedure* and the stakes of refusing — not which probes are ties, which
  it must still discover by reading the silos, so the study stays within policy execution.

The two prompts differ only in that block (`tests/test_task.py` pins it), so a paired run
isolates the scaffold.

## Design

- **Instrument.** The `meridian` family: the authored org (seed 0) plus four scenario-
  factory variants (seeds 1–4, [ADR-0008](adr/0008-scenario-factory-and-holdout-protocol.md)),
  each re-dealing the conflict graph and synthesizing fresh anti-prior values while holding
  the 6/6/5/5 category counts fixed. Five instances × 22 probes = **110 probe-instances per
  model per arm**, five per conflict type per seed rather than one — the n=1-per-type
  weakness of a single org is retired.
- **Models.** Four API models under the frozen `det-4`, k=3, strict pass^3 protocol:
  claude-sonnet-4-6, claude-haiku-4-5, gpt-4o, gpt-4o-mini. Run 2026-06-28.
- **Statistic.** Each (seed, probe) is graded as strict pass^3 under each arm and the two
  arms are paired on it. *Net correct behaviour* is the fraction of probe-instances that
  pass. The arms are compared with an exact McNemar test over the discordant pairs (the
  probe-instances one arm passes and the other fails); the per-type breakdown keeps refusal
  gains and answering losses separately visible.

## Result — net correct behaviour and the per-type profile (pooled over 5 seeds)

| Model | arm | net pass^3 | none | resolvable | unresolvable | void | McNemar (helped/hurt) | exact p |
|---|---|--:|--:|--:|--:|--:|:--:|--:|
| claude-sonnet-4-6 | B0 | 75.5% | 90% | 86.7% | 20% | 100% | | |
| claude-sonnet-4-6 | **R1** | **95.5%** | 93.3% | 100% | **88%** | 100% | 24 / 2 | **< 0.0001** |
| gpt-4o | B0 | 44.5% | 0% | 73.3% | 16% | 92% | | |
| gpt-4o | **R1** | **52.7%** | 0% | 73.3% | **48%** | 96% | 10 / 1 | **0.012** |
| claude-haiku-4-5 | B0 | 52.7% | 53.3% | 63.3% | 4% | 88% | | |
| claude-haiku-4-5 | R1 | 54.5% | 53.3% | 43.3% | 36% | 88% | 17 / 15 | 0.86 |
| gpt-4o-mini | B0 | 32.7% | 0% | 36.7% | 0% | 100% | | |
| gpt-4o-mini | R1 | 29.1% | 0% | 23.3% | 0% | 100% | 2 / 6 | 0.29 |

## Findings

1. **The scaffold works, and the effect scales with capability.** For the two more capable
   models the refusal-aware scaffold is a large, significant gain in net correct behaviour:
   claude-sonnet-4-6 rises 75.5% → 95.5% (McNemar 24–2, p < 0.0001) and gpt-4o 44.5% →
   52.7% (10–1, p = 0.012). The mechanism is visible in the `unresolvable` column — the
   symmetric ties on which the leaderboard's central failure sits. Sonnet goes from
   fabricating a tie-break four times in five (20% reliable refusal) to refusing nearly
   every tie (88%); gpt-4o triples its tie-refusal (16% → 48%). Naming the taxonomy and the
   stakes of refusing converts a model that *can* read the conflict from confident
   fabrication to committed abstention.

2. **On weaker models the gain is paid for elsewhere — or not realized.** claude-haiku-4-5
   improves on ties exactly as the capable models do (4% → 36%) but loses an almost equal
   amount on `resolvable` (63.3% → 43.3%): the same instruction that makes it refuse true
   ties also makes it over-refuse conflicts it should have resolved, so net correct
   behaviour barely moves (52.7% → 54.5%, p = 0.86) — a wash, not a win. gpt-4o-mini never
   benefits on ties at all (0% → 0%): it fails upstream at the cross-silo joins (`none` 0%),
   so it cannot reach the point where a tie is recognizable, and the scaffold only nudges
   it toward slightly more over-refusal on `resolvable` (36.7% → 23.3%), a small net
   regression (p = 0.29, n.s.). The refusal-aware scaffold is a *capability amplifier*, not
   a capability substitute.

3. **The honest summary is conditional.** Averaged blindly across all four models the
   scaffold looks modest; read per model it is decisive for the capable two and a
   capability-dependent trade for the rest. The per-type table, not a single pooled number,
   is the result.

*Independence note: pairing is within a (seed, probe) instance, and the k=3 repetitions are
collapsed to one strict pass^3 outcome before pairing, so the McNemar test is not
pseudo-replicated across epochs. Different seeds synthesize different values for the same
probe slot, so instances are near-independent; residual structural correlation across seeds
sharing a slot is a known, small caveat.*

## Holdout — the same effect on a committed, unseen instance

To show the result is not an artifact of instances visible while authoring the scaffold,
the headline model was re-run on a **withheld** factory seed under the holdout protocol
(ADR-0008). Before the run, only a salted commitment to the seed was recorded:

```
commitment = SHA-256(factory_version ‖ 0x00 ‖ seed ‖ 0x00 ‖ salt)
           = df55a1901cdeaf7daa96944ba05080523f6df635cb350a82b1f55c826331ce82
factory_version = fac-1     date = 2026-06-28     (seed and salt sealed)
```

After the run the reveal `{seed = 31337, salt, factory_version = fac-1}` recomputes the
commitment (`verify() → True`) and regenerates the exact org and answer key, proving the
graded instance was fixed in advance. On that genuinely unseen instance the scaffold effect
replicates:

| arm | net pass^3 | none | resolvable | unresolvable | void |
|---|--:|--:|--:|--:|--:|
| B0 | 86.4% | 100% | 100% | 40% | 100% |
| **R1** | **95.5%** | 83% | 100% | **100%** | 100% |

The commitment, the reveal, and the verification are in
[`logs/scaffold/holdout/`](../logs/scaffold/holdout/).

## Limitations

- **Four API models.** qwen3.5 (the open-weights leaderboard row) is not re-run here; the
  claim is about API models on 2026-06-28.
- **Over-refusal is real.** R1 raises refusal as an outcome, and on weaker models that
  bleeds into `resolvable` cases. A scaffold that improved ties without that cost is future
  work; the per-type table is published precisely so the cost is not hidden in the net.
- **One org family.** Five instances of `meridian` retire n=1-per-type but remain one
  authored family; breadth across distinct org shapes is still future work.

## Reproduce

```bash
# one arm, one seed, one model
.venv/bin/inspect eval src/tessera/evals/task.py@tessera_probes \
  --model anthropic/claude-sonnet-4-6 -T org=meridian -T k=3 -T seed=0 \
  -T scaffold=refusal_aware --log-dir logs/scaffold
# the full matrix + paired analysis
scripts/scaffold/run.sh <seed> <baseline|refusal_aware> <provider/model> ...
.venv/bin/python scripts/scaffold/analyze.py
```
