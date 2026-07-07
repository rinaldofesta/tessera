# Committed leaderboard logs

Inspect `.eval` logs that **back** rows in [`../../docs/leaderboard.rows.json`](../../docs/leaderboard.rows.json)
— the evidence that a published row's numbers are a real run's output, not a hand-typed
figure (ADR-0012, the delivery of the `log` provenance field ADR-0010 introduced).

The rest of `logs/` is gitignored (local only); this directory and `*.eval` files inside
it are the exception, exactly like the holdout `COMMITMENT.json`/`REVEAL.json`.

## Backing a row

1. Drop the run's `.eval` here, named for its row (e.g. `claude-sonnet-4-6.eval`).
2. From the repo root, extract the row — the numbers come straight from the log and the
   path is stamped repo-relative:
   ```bash
   .venv/bin/tessera-leaderboard --extract logs/leaderboard/claude-sonnet-4-6.eval
   ```
3. Merge the emitted row into `docs/leaderboard.rows.json` (its `log` is now
   `{"path": "logs/leaderboard/claude-sonnet-4-6.eval", "sha256": "…"}`).
4. Verify:
   ```bash
   .venv/bin/tessera-leaderboard --manifest docs/leaderboard.rows.json --verify
   ```
   CI runs the same check: for every row with a non-null `log`, it re-derives the row from
   the committed log and fails on any digest or metric mismatch. Rows with `log: null` are
   reported as unbacked, not failures — enforcement turns on the moment a log lands.
