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

Reproduce the report from the log with no API key:

```bash
uv run tessera-report src/tessera/data/examples/first-contact/log.eval
```

The bundled `toy` and `meridian` suites live in `src/tessera/examples/`; create an
editable suite with `tessera init NAME`. See the README section "Bring your own data".
