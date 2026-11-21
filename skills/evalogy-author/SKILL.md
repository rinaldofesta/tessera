---
name: evalogy-author
description: Author and validate an Evalogy reliability suite
---

# Author a suite

1. Create a safe, non-builtin suite name:

   ```sh
   evalogy init NAME
   ```

2. Edit `~/.evalogy/suites/NAME.json`. Its top level is a `claims` list and a `probes` list. A claim uses `claim_id`, `subject`, `predicate`, `value`, `silo`, optional `asserted_at` and `authority`, and `render` with `as` plus an optional prose `template`. A probe uses `probe_id`, `question`, `references`, `conflict_type`, optional `resolution_rule`, `expected_behavior`, `expected_answer`, and `expected_sources`.

3. Plant a conflict that tests a real decision. A good `unresolvable` case puts different values in separate silos with equal authority and no recency winner, so refusal is the only honest outcome. A good `resolvable` case makes the winning recency or authority rule explicit. Avoid trivia, ambiguous expected answers, and conflicts a single source can settle accidentally.

4. Validate both the JSON model and its in-memory compile:

   ```sh
   evalogy validate NAME
   ```

   Fix every located issue before running.

5. Confirm the plan, then evaluate:

   ```sh
   evalogy run --model MODEL --suite NAME --dry-run --json
   evalogy run --model MODEL --suite NAME
   ```
