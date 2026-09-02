---
name: tessera-publish
description: Publish and compare Tessera reliability results with reproducible evidence
---

# Share results

1. Render the stored run as Markdown:

   ```sh
   tessera report REF > scorecard.md
   ```

   Share the verdict and scorecard together; do not reduce a result to mean accuracy alone.

2. Compare paired results only with the comparability gate:

   ```sh
   tessera compare A B --require-comparable --json
   ```

   Comparable runs use the same scorer version, suite, `k`, scaffold, and seed. Exit 1 means the requested comparison gate rejected a mismatch.

3. Back a leaderboard row with the committed `.eval` log. Extract its metrics and repository-relative digest:

   ```sh
   tessera leaderboard extract logs/leaderboard/RUN.eval --label LABEL --note NOTE
   ```

   This prints the row as JSON (`-o FILE` writes it to a file instead of stdout); merge it into `docs/leaderboard.rows.json` by hand — never hand-edit `docs/leaderboard.md` itself.

4. Regenerate and verify:

   ```sh
   tessera leaderboard render --manifest docs/leaderboard.rows.json -o docs/leaderboard.md
   tessera leaderboard verify --manifest docs/leaderboard.rows.json
   ```

   Verification re-derives every log-backed row and checks its committed path, SHA-256 digest, and metrics.
