# ADR-0001 — The epoch count and the pass^k reducer live together in the task

- **Date**: 2026-06-11
- **Status**: Accepted

## Context

Tessera's headline metric is strict pass^k: a probe passes only if every one of its k
epochs passes. That requires two settings to agree — the epoch *count* and the
`pass_k(k)` *reducer* that aggregates the epochs.

inspect_ai merges them independently (verified on the installed 0.3.235,
`inspect_ai/_eval/run.py:165-184`): an eval-level `eval(epochs=N)` override replaces
the count but **keeps the task's reducer**. With the reducer pinned at `pass_k(3)`,
`epochs=2` hard-errors at runtime ("Reducer 'pass_k_3' requires 3 epochs") and
`epochs=5` runs silently with a mislabeled metric — pass^3 computed over 5 epochs.
The product API hit exactly this: the UI's epochs slider forwarded an eval-level
override and diverged from the task's reducer.

## Decision

The task owns both halves through a single parameter:

```python
tessera_probes(judge=..., org=..., k=3)   # builds Epochs(k, [pass_k(k), "mean"])
```

- CLI: `inspect eval tessera/evals -T k=5` (the value arrives as a string; the task
  coerces and validates `k >= 1`).
- API runner: passes `task_args={"k": request.epochs}` and **never** the eval-level
  `epochs` kwarg. `RunRequest.epochs` is validated to 1..10.

## Consequences

- Count and reducer cannot diverge; the log's registered reducer name (`pass_k_5`)
  always matches the actual epoch count, and the scorecard labels follow.
- Sweeping k is one flag: `for k in 1 3 5 10; do ... -T k=$k; done`.
- Anyone driving the task directly must use `-T k=N`, not `--epochs` — the eval-level
  override is exactly the foot-gun this ADR removes.
