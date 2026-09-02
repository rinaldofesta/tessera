---
name: tessera-run
description: Run a Tessera reliability evaluation and read the verdict
---

# Run a reliability evaluation

1. Plan before spending model calls:

   ```sh
   tessera run --model MODEL --suite starter --dry-run --json
   ```

   Read `ready` and every entry in `blockers`. A dry-run is advisory and exits 0 even when `ready` is false.

2. If the plan is blocked on a provider, follow its `fix`. Pass the key over standard input, never argv:

   ```sh
   printf '%s' "$KEY" | tessera connect anthropic --key-stdin
   ```

3. Run the same request without `--dry-run`:

   ```sh
   tessera run --model MODEL --suite starter
   ```

4. Read the verdict sentence first. Then compare strict `pass^k`, which requires every repetition to pass, with `mean`, which shows occasional capability.

5. When the run is a release gate, state the threshold explicitly:

   ```sh
   tessera run --model MODEL --suite starter --min-pass-k 0.9 --json
   ```

   Exit 1 means this requested threshold failed. Without a gate, an unreliable completed run exits 0.

6. Parse `tessera report REF --json` from these fields: `verdict.sentence`, `verdict.pass_k_rate`, `verdict.mean_rate`, `report.categories`, `report.probes`, `diagnostics`, `receipt`, `request`, and `paths`. Treat `ok` as operational completion, not as a reliability claim.
