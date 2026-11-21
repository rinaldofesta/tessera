# Writing a suite

A suite is a small set of questions with conflicts planted in the source material, so you know in advance when the agent should answer and when it should refuse. Evalogy includes `starter` and the larger `meridian` suite.

```console
evalogy init NAME
# edit ~/.evalogy/suites/NAME.json
evalogy validate NAME
evalogy run --model anthropic/claude-sonnet-4-6 --suite NAME
```

The JSON follows this top-level shape:

```json
{
  "claims": [{"claim_id": "…", "subject": "…", "predicate": "…", "value": "…", "silo": "…", "render": {"as": "field"}}],
  "probes": [{"probe_id": "…", "question": "…", "references": ["…"], "conflict_type": "none", "expected_behavior": "answer", "expected_answer": "…", "expected_sources": ["…"]}]
}
```

Each claim's `silo` says which company source holds it. Optional claim fields are `asserted_at` and `authority`; a resolvable probe also uses `resolution_rule`.
