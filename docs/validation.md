# Transfer analyzer

`tessera-validate-transfer` computes the public synthetic-to-real analysis without reading
prompts, documents, transcripts, CRM records, or candidate records. Its input contains one
collapsed score per task and configuration for each suite.

The complete seven-configuration worked example is
[`examples/validation-study.example.json`](../examples/validation-study.example.json). CI
runs it through the installed command:

```bash
tessera-validate-transfer examples/validation-study.example.json -o result.md
tessera-validate-transfer examples/validation-study.example.json --json -o result.json
```

Exit status 2 means the study or rendered result violates the analysis contract. Status 1
means the input could not be read or the output could not be written.

The registered input must contain 7 to 10 configurations. Task IDs are opaque and
non-identifying. Each configuration's `tessera_task_scores` and `real_task_scores` is an
object keyed by those IDs, not a positional array. The analyzer rejects a missing or extra
ID and normalizes JSON object order before bootstrapping. Validation errors report counts,
not identifier contents. Scores are finite values from 0 to 1. Repetitions are collapsed
before this file is assembled.

`bootstrap.draws` and `bootstrap.seed` are mandatory. Draws must equal the registered value
of 10,000; the analyzer has no fallback seed. Reported ranks use standard competition ranking
(`1, 1, 3` after a tie). A top-three boundary tie is disclosed and resolved by natural
ascending configuration ID, so `config-9` precedes `config-10`.

The output includes the point tau-b, one-sided lower bound, pre-registered claim sentence,
score intervals, top-three overlap, every decisive pair, the decisive denominator, and every
dropped configuration. It never contains task text.
