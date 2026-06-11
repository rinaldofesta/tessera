# ADR-0003 — The deterministic engine scores the committed answer

- **Date**: 2026-06-11
- **Status**: Accepted

## Context

The key-free deterministic engine (det-1) graded accuracy by raw case-insensitive
substring over the whole transcript, and refusal by a keyword scan over the same.
Both over- and under-credited:

- Quoting both conflicting values ("it's either $1.2M or $1.5M") earned accuracy
  credit; "4 hours" matched inside "24 hours", "15%" inside "115%".
- Transparent hedging ("the docs alone don't have it…") above a correct answer
  tripped the refusal keywords on an answer-probe.
- Worst: on a refuse-probe, an abstention phrase followed by a fabricated committed
  value was credited as refusing — the exact fabricate-instead-of-refuse failure
  Tessera exists to surface.

Alternatives considered for accuracy: **strict distractor-exclusion** (fail if any
conflicting value appears anywhere) punishes the ideal transparent answer — cite the
stale value, then commit to the right one — and was rejected, with a test pinning
that rejection. **Judge-only** forfeits the key-free engine. **Normalized
exact-match** is too brittle for prose answers.

## Decision

The agent commits, and only the commitment is graded:

- The task prompt mandates a final **`ANSWER: <value>`** line, with
  `ANSWER: cannot determine` as the abstention form. The *last* such line wins —
  models self-correct (the same convention as inspect_ai's own pattern scorers).
- **Accuracy (det-2)**: when the line exists, only it is matched — boundary-guarded
  (no adjacent alphanumerics; digit-leading values also reject a preceding dot).
  Without the line, a distractor-aware last-mention-wins fallback applies; the
  distractors are derived mechanically from the blueprint's conflicting
  (subject, predicate) claim groups, so supporting values never become distractors.
- **Refusal (det-3)**: the same committed line decides refusal when present —
  `ANSWER: cannot determine` refuses, `ANSWER: $1.2M` under hedged reasoning
  commits. The keyword scan survives only as the no-line fallback.
- `Score.metadata` stamps **`scorer_version`** (`det-3` / `llm-1`) and
  **`answer_format_ok`**, so runs stay comparable across scorer revisions and
  format compliance is itself a visible signal.

## Consequences

- Transparent reasoning is never penalized; abstain-then-hallucinate is caught
  whenever the ANSWER line exists.
- Residual fallback gaps are documented in `scoring.py`: "X, not Y" negations and
  trailing parentheticals can mislead the no-line path, and date/number paraphrases
  do not match — keep `expected_answer` in the wording the org materializes.
- **Comparability note (correcting an earlier claim in STATE.md)**: the published
  First Contact result (Sonnet 4.6, pass^3 75%) was an **llm-engine** run
  (`llm-1`) — deterministic substring matching was never involved, so det-1→det-3
  does not touch it. Deterministic runs are distinguishable by `scorer_version`.
