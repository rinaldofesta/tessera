# examples/

The committed proof behind the README. Everything here is read by tests and CI, so it
changes only through a reviewed PR — never by hand-editing a number.

The Inspect logs now live in package data as complete, read-only run folders:
[`first-contact`](../src/tessera/data/examples/first-contact/) and
[`gpt-4o`](../src/tessera/data/examples/gpt-4o/). Each folder contains `log.eval`,
`run.json`, `report.json`, `receipt.json`, and `report.md`.

| File | What it is | Used by |
|---|---|---|
| `first-contact-report.md` | The Markdown report rendered from that log, committed verbatim. | README links; its sha256 is pinned by the receipt |
| `first-contact.receipt.json` | The publication receipt: sha256 of the log and the report, git revision of the run, toy-org blueprint and compiled-artifact digests, review notes. | `tests/test_pinned_examples.py` checks every digest against the files |
| `validation-study.example.json` | Input for the transfer-validation analyzer (ADR-0013): Tessera scores next to real-task scores for a handful of configs. | `tests/research/test_validation_analysis.py` |
| `suites/starter.json` | The complete four-question Starter suite exported from the built-in builder. | Small runnable reference and reproducibility test |
| `suites/meridian.json` | The complete 22-question Meridian suite exported from the built-in builder. | Full-size runnable reference and reproducibility test |
| `suites/my-company.json` | A complete authored suite copied from the packaged `tessera init` template. | Starting point for hand-authored suites |

Reproduce the report from the log with no API key:

```bash
uv run tessera report first-contact
```

The built-in `toy` and `meridian` builders live in `src/tessera/examples/`; their tracked
exports are under `examples/suites/`. Create an editable suite with `tessera init NAME`.
See the README section "Bring your own data".
