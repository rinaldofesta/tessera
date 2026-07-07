# Tessera leaderboard — meridian

Results as of 2026-07-06. Deterministic engine (`det-4`), k=3: the headline is **strict pass^3** — a probe counts only if it passed every one of its 3 repetitions; `mean` alongside is capability when the dice land well. Protocol: [ADR-0006](adr/0006-meridian-and-the-leaderboard-protocol.md).

| # | Model | harness | pass^3 | mean | none | resolvable | unresolvable | void | ANSWER fmt | scorer | run date | notes |
|--:|---|---|--:|--:|--:|--:|--:|--:|--:|---|---|---|
| 1 | anthropic/claude-fable-5 | single | **100%** | 100% | 100% | 100% | 100% | 100% | 100% | det-4 | 2026-07-06 |  |
| 2 | anthropic/claude-opus-4-8 | single | **100%** | 100% | 100% | 100% | 100% | 100% | 100% | det-4 | 2026-07-06 |  |
| 3 | anthropic/claude-sonnet-4-6 | single | **86.4%** | 90.9% | 100% | 100% | 40% | 100% | 98.5% | det-4 | 2026-06-11 |  |
| 4 | moa/max (gpt-5.5+deepseek-v4-pro+glm-5.2 to opus-4.8) | ensemble | **81.8%** | 89.4% | 66.7% | 100% | 60% | 100% | 100% | det-4 | 2026-07-06 | MoA ensemble via local shim; refs advisory-only, aggregator holds tools |
| 5 | anthropic/claude-sonnet-5 | single | **77.3%** | 86.4% | 100% | 100% | 0% | 100% | 100% | det-4 | 2026-07-06 |  |
| 6 | anthropic/claude-haiku-4-5 | single | **54.5%** | 68.2% | 66.7% | 66.7% | 0% | 80% | 3% | det-4 | 2026-06-12 | fabricates on all five ties; grades ride the fallback path |
| 7 | ollama/qwen3.5:latest | single | **45.5%** | 71.2% | 83.3% | 33.3% | 0% | 60% | 43.9% | det-4 | 2026-06-12 | open-weights 9.7B Q4_K_M, local via Ollama; diligent reader (provenance 98%) but 5 of 12 failed probes are fallback strictness on format-noncompliant answers — the det-5 candidate |
| 8 | openai/gpt-4o | single | **45.5%** | 54.5% | 0% | 83.3% | 0% | 100% | 22.7% | det-4 | 2026-06-12 | skips the CRM leg of cross-silo joins (8 of 12 failed probes) |
| 9 | openai/gpt-4o-mini | single | **27.3%** | 40.9% | 0% | 16.7% | 0% | 100% | 92.4% | det-4 | 2026-06-12 | fails the joins and all five ties |

> Rows with a non-`single` `harness` ran the identical protocol (same org, k, scorer, scaffold, seed) as the single-model rows — they are comparable and ranked together; the `harness` column discloses how each row's model calls were dispatched (e.g. an ensemble of advisory models with an aggregator that commits the answer). Comparability rides on the guarded dimensions, not on the harness (ADR-0011).

## Methodology

- Every row is one run of the `meridian` org: all probes, 3 epochs each, scored on accuracy, provenance (mechanical, per-field for the CRM — credited only for data that actually came back), and committed refusal.
- The per-category columns are strict pass^k by conflict type. `unresolvable` is the column to watch: it measures whether a model fabricates a tie-break rather than refusing when two systems of record disagree with equal authority.
- The `meridian` blueprint is public — it is the answer key. Honesty over purity: results are date-stamped, training-data contamination becomes more likely over time, and seeded variants are the planned mitigation (see ADR-0006).
- Tessera scores policy execution, not discovery: the agent is told the reconciliation policy; the question is whether it executes it reliably.
- `ANSWER fmt` is compliance with the committed-answer contract (a final `ANSWER: <value>` line, the org's exact wording). Low-compliance rows were graded mostly by the documented fallback (distractor-aware, last-mention-wins), which is stricter about paraphrase — format discipline is part of what is being measured.

This file is generated from [`leaderboard.rows.json`](leaderboard.rows.json) — the committed source of truth (ADR-0010). Never edit the table by hand; CI regenerates it from the manifest and fails on drift. To add or update a row, produce a run, extract its row (numbers guaranteed to match the log), merge it into the manifest, then regenerate:

```bash
.venv/bin/inspect eval src/tessera/evals/task.py@tessera_probes \
  --model <provider/model> -T org=meridian -T judge=deterministic -T k=3 \
  -T seed=0 -T scaffold=baseline --log-dir logs
.venv/bin/tessera-leaderboard --extract logs/<run>.eval   # -> a manifest row (JSON)
.venv/bin/tessera-leaderboard --manifest docs/leaderboard.rows.json -o docs/leaderboard.md
```
