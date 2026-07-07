# Tessera leaderboard — meridian

Results as of 2026-07-06. Deterministic engine (`det-4`), k=3: the headline is **strict pass^3** — a probe counts only if it passed every one of its 3 repetitions; `mean` alongside is capability when the dice land well. Protocol: [ADR-0006](adr/0006-meridian-and-the-leaderboard-protocol.md).

| # | Model | pass^3 | mean | none | resolvable | unresolvable | void | ANSWER fmt | scorer | run date | notes |
|--:|---|--:|--:|--:|--:|--:|--:|--:|---|---|---|
| 1 | anthropic/claude-fable-5 | **100%** | 100% | 100% | 100% | 100% | 100% | 100% | det-4 | 2026-07-06 |  |
| 2 | anthropic/claude-opus-4-8 | **100%** | 100% | 100% | 100% | 100% | 100% | 100% | det-4 | 2026-07-06 |  |
| 3 | anthropic/claude-sonnet-4-6 | **86.4%** | 90.9% | 100% | 100% | 40% | 100% | 98.5% | det-4 | 2026-06-11 |  |
| 4 | anthropic/claude-sonnet-5 | **77.3%** | 86.4% | 100% | 100% | 0% | 100% | 100% | det-4 | 2026-07-06 |  |
| 5 | anthropic/claude-haiku-4-5 | **54.5%** | 68.2% | 66.7% | 66.7% | 0% | 80% | 3% | det-4 | 2026-06-12 | fabricates on all five ties; grades ride the fallback path |
| 6 | ollama/qwen3.5:latest | **45.5%** | 71.2% | 83.3% | 33.3% | 0% | 60% | 43.9% | det-4 | 2026-06-12 | open-weights 9.7B Q4_K_M, local via Ollama; diligent reader (provenance 98%) but 5 of 12 failed probes are fallback strictness on format-noncompliant answers — the det-5 candidate |
| 7 | openai/gpt-4o | **45.5%** | 54.5% | 0% | 83.3% | 0% | 100% | 22.7% | det-4 | 2026-06-12 | skips the CRM leg of cross-silo joins (8 of 12 failed probes) |
| 8 | openai/gpt-4o-mini | **27.3%** | 40.9% | 0% | 16.7% | 0% | 100% | 92.4% | det-4 | 2026-06-12 | fails the joins and all five ties |

## Out-of-protocol exhibitions

Configurations measured on the same org, scorer, and k, but outside the single-model baseline protocol of ADR-0006 — a multi-model ensemble is architecturally a scaffold-level intervention, and the executable comparability guard cannot yet represent it as one. Exhibition rows are shown here unranked rather than inside the table above; they rejoin the ranked table when the harness dimension becomes an executable guard (see the roadmap in STATE.md).

| Configuration | pass^3 | mean | none | resolvable | unresolvable | void | ANSWER fmt | scorer | run date | notes |
|---|--:|--:|--:|--:|--:|--:|--:|---|---|---|
| moa/max (gpt-5.5+deepseek-v4-pro+glm-5.2 to opus-4.8) | **81.8%** | 89.4% | 66.7% | 100% | 60% | 100% | 100% | det-4 | 2026-07-06 | MoA ensemble via local shim; refs advisory-only, aggregator holds tools |

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
