# ADR-0007 — Reliability under delegation: a two-stage chain, not handoff()

- **Date**: 2026-06-12
- **Status**: Accepted (shipped as `tessera_probes_delegated`)

## Context

Every Tessera result so far measures a *single* agent against the org. Real
enterprise deployments increasingly delegate: one agent researches, another acts on
the findings. The single-agent meridian baseline gives the experiment its signal for
free — on the unresolvable tie the producer fabricates a precedence rule in roughly
one epoch in three — so the question is measurable today: **does the refusal flag
survive a handoff, and does a fabricated answer get laundered into settled fact?**

The MVP is the smallest topology that can answer it: a **producer** with the MCP
tools researches and submits a brief; a **consumer** with *no* tool access commits
the final answer from that brief alone. Two invariants make the experiment valid:

1. **The scorer must see the producer's real tool traffic** — provenance is
   mechanical (det-4, per-field, response-based) and must keep measuring the stage
   that actually touched the systems.
2. **The consumer must see only the brief** — if the raw tool results leak to the
   consumer, "did the conflict survive the hop" is unmeasurable, because nothing
   was actually delegated.

## Decision

**`inspect_ai.agent.handoff()` is rejected** — verified on the installed 0.3.235,
it cannot satisfy both invariants at once:

- Its default `content_only` output filter converts the sub-agent's `ToolCall`s to
  plain text and its `ChatMessageTool`s to user messages, so the producer's traffic
  would not survive as structured tool events and provenance would always fail.
- The failure is structural, not a flag: handoff shares ONE conversation between
  parent and sub-agent. Disabling the filter restores the tool events — for the
  scorer *and* for the consumer alike. The scorer's view and the consumer's view
  cannot diverge under handoff.

Instead, a custom chain (`evals/delegation.py`) composes two `react()` agents via
`inspect_ai.agent.run()`:

1. Run the producer on the probe; it is **exactly the direct task's agent** — same
   prompt, same tools, same submit contract — so the direct baseline is the clean
   counterfactual.
2. Store the producer's submitted brief in the per-sample `store()` (solver↔scorer
   channel) and build the consumer's input: the question + the brief, nothing else.
3. Run the tool-less consumer on that brief. Its prompt carries the SAME
   reconciliation policy and ANSWER-line contract as the producer, so degradation
   is attributable to the hop, not to a softer contract.
4. Merge: `state.messages = producer.messages + consumer.messages`,
   `state.output = consumer.output`.

Scoring needs no new engine. det-4 applies unchanged to the merged transcript —
provenance reads the producer's tool events, accuracy/refusal read the consumer's
committed line — and `delegated_score_attempt` adds two hop flags from the stored
brief, splitting refuse-probe failures by where the fabrication originated:

- **`flag_dropped`** — the producer held the line ("cannot determine"); the
  consumer committed anyway. The hop destroyed a correct abstention.
- **`conflict_laundered`** — the producer already fabricated; the consumer relayed
  it as settled fact. The hop turned a flagged guess into a confident answer.

The task is a separate `@task tessera_probes_delegated(org, k)` (deterministic
engine only for the MVP): the published direct task's signature stays frozen, and
both tasks share org compilation via `_compiled_org`. `scorer_version` stays
`det-4` — the engine semantics are identical, which is precisely what makes
direct-vs-delegated rows comparable in one table.

## Alternatives considered

- **`handoff()` with `output_filter=None`**: restores tool events but shows them to
  the consumer too — invariant 2 dies, nothing is delegated. Rejected.
- **A `mode` argument on `tessera_probes`**: one task, two behaviors. Rejected —
  the direct task is the published benchmark entry point; a mode flag invites
  accidental protocol drift, and a separate task addresses cleanly from the CLI.
- **A consumer with tools**: closer to some real topologies, but it confounds the
  hop with re-research — the consumer could repair the producer's fabrication by
  re-reading the systems, and the flags would measure nothing crisp. Deferred.

## Consequences

- Non-goals of the MVP, explicitly: a single hop only; no tool-using consumer; no
  coordinator/pyramid topologies; no cross-model pairs (producer and consumer run
  the same model). Each is a follow-up once the single-hop number exists.
- The comparison artifact (`docs/delegation.md`) pairs a delegated run against the
  direct baseline of the SAME model/org/k/scorer_version, rendered by the same
  `tessera-leaderboard` generator — the comparability guard applies to the pair.
- The chain bypasses handoff's transcript niceties; in exchange the experiment is
  honest. The producer/consumer stages remain visible in the log via their agent
  span names.
- The hop flags live in `Score.metadata` next to the axes, so the report layer
  carries them without schema changes; adjudication reads them per epoch.
