# Tessera leaderboard — meridian

Results as of 2026-06-12. Deterministic engine (`det-4`), k=3: the headline is **strict pass^3** — a probe counts only if it passed every one of its 3 repetitions; `mean` alongside is capability when the dice land well. Protocol: [ADR-0006](adr/0006-meridian-and-the-leaderboard-protocol.md).

| # | Model | pass^3 | mean | none | resolvable | unresolvable | void | ANSWER fmt | scorer | run date | notes |
|--:|---|--:|--:|--:|--:|--:|--:|--:|---|---|---|
| 1 | anthropic/claude-sonnet-4-6 | **86.4%** | 90.9% | 100% | 100% | 40% | 100% | 98.5% | det-4 | 2026-06-11 |  |
| 2 | anthropic/claude-haiku-4-5 | **54.5%** | 68.2% | 66.7% | 66.7% | 0% | 80% | 3% | det-4 | 2026-06-12 | fabricates on all five ties; grades ride the fallback path |
| 3 | ollama/qwen3.5:latest | **45.5%** | 71.2% | 83.3% | 33.3% | 0% | 60% | 43.9% | det-4 | 2026-06-12 | open-weights 9.7B Q4_K_M, local via Ollama; diligent reader (provenance 98%) but 5 of 12 failed probes are fallback strictness on format-noncompliant answers — det-5 candidate |
| 4 | openai/gpt-4o | **45.5%** | 54.5% | 0% | 83.3% | 0% | 100% | 22.7% | det-4 | 2026-06-12 | skips the CRM leg of cross-silo joins (8 of 12 failed probes) |
| 5 | openai/gpt-4o-mini | **27.3%** | 40.9% | 0% | 16.7% | 0% | 100% | 92.4% | det-4 | 2026-06-12 | fails the joins and all five ties |

## Methodology

- Every row is one run of the `meridian` org: all probes, 3 epochs each, scored on accuracy, provenance (mechanical, per-field for the CRM — credited only for data that actually came back), and committed refusal.
- The per-category columns are strict pass^k by conflict type. `unresolvable` is the column to watch: it measures whether a model fabricates a tie-break rather than refusing when two systems of record disagree with equal authority.
- The `meridian` blueprint is public — it is the answer key. Honesty over purity: results are date-stamped, training-data contamination becomes more likely over time, and seeded variants are the planned mitigation (see ADR-0006).
- Tessera scores policy execution, not discovery: the agent is told the reconciliation policy; the question is whether it executes it reliably.
- `ANSWER fmt` is compliance with the committed-answer contract (a final `ANSWER: <value>` line, the org's exact wording). Low-compliance rows were graded mostly by the documented fallback (distractor-aware, last-mention-wins), which is stricter about paraphrase — format discipline is part of what is being measured.

Reproduce a row, then regenerate this file:

```bash
.venv/bin/inspect eval src/tessera/evals/task.py@tessera_probes \
  --model <provider/model> -T org=meridian -T judge=deterministic -T k=3 \
  -T seed=0 -T scaffold=baseline --log-dir logs
.venv/bin/tessera-leaderboard logs/<run>.eval [logs/<run>.eval ...] -o docs/leaderboard.md
```
