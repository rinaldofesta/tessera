# examples/

The committed proof behind the README. Everything here is read by tests and CI, so it
changes only through a reviewed PR — never by hand-editing a number.

| File | What it is | Used by |
|---|---|---|
| `first-contact.eval` | The inspect_ai log of the First Contact run (2026-06-04): `anthropic/claude-sonnet-4-6`, toy org, 4 probes × 3 epochs, LLM grading with `openai/gpt-4o`. | README scorecard, CI quickstart, `tests/test_pinned_examples.py` (headline numbers, public origin, no credential-like values) |
| `first-contact-report.md` | The Markdown report rendered from that log, committed verbatim. | README links; its sha256 is pinned by the receipt |
| `first-contact.receipt.json` | The publication receipt: sha256 of the log and the report, git revision of the run, toy-org blueprint and compiled-artifact digests, review notes. | `tests/test_pinned_examples.py` checks every digest against the files |
| `gpt-4o.eval` | The same protocol run on `openai/gpt-4o` — the second arm of the comparison example. | `tests/test_pinned_examples.py` (headline numbers); compare examples |
| `validation-study.example.json` | Input for the transfer-validation analyzer (ADR-0013): Tessera scores next to real-task scores for a handful of configs. | CI quickstart, `tests/test_validation_analysis.py` |

Reproduce the report from the log with no API key:

```bash
uv run tessera-report examples/first-contact.eval
```

Suites (the org blueprints — `toy`, `meridian`, `your_org`) live in
`src/tessera/examples/`; see the README section "Bring your own data".
