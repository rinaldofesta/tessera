# Transfer analyzer

`tessera-validate-transfer` computes the public synthetic-to-real analysis without reading
prompts, documents, transcripts, CRM records, or candidate records. Its input contains one
collapsed score per task and configuration for each suite.

```json
{
  "study_id": "transfer-2026-q4",
  "tessera_task_ids": ["tessera-01", "tessera-02", "tessera-03"],
  "real_task_ids": ["real-01", "real-02", "real-03"],
  "bootstrap": {"draws": 10000, "seed": 20260823},
  "configs": [
    {
      "id": "ollama-qwen3.5-baseline",
      "tessera_task_scores": [1, 0, 1],
      "real_task_scores": [0.72, 0.61, 0.83]
    }
  ],
  "dropped": [
    {"id": "anthropic-sonnet-4-6-baseline", "reason": "snapshot unreachable after freeze"}
  ]
}
```

The real registered input must contain 7 to 10 configurations. Task IDs are opaque,
non-identifying IDs in frozen order; they make score alignment checkable without publishing
task text. Within one suite every configuration must have one score for every registered task
ID. Scores are finite values from 0 to 1. Repetitions are collapsed before this file is
assembled.

```bash
tessera-validate-transfer study.json -o result.md
tessera-validate-transfer study.json --json -o result.json
```

The output includes the point tau-b, one-sided lower bound, pre-registered claim sentence,
score intervals, top-three overlap, every decisive pair, the decisive denominator, and every
dropped configuration. It never contains task text.
