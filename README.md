# Tessera

**Tessera checks whether an AI agent gets the right answer every time when the company's own sources disagree.**

> *tessera* (n.): a single tile of a mosaic. No tile is the picture. The picture is how they fit.

[![ci](https://github.com/rinaldofesta/tessera/actions/workflows/ci.yml/badge.svg)](https://github.com/rinaldofesta/tessera/actions/workflows/ci.yml)
[![release](https://img.shields.io/badge/release-v0.3.0-brightgreen)](CHANGELOG.md)
[![pypi](https://img.shields.io/badge/pypi-tessera--eval-blue)](https://pypi.org/project/tessera-eval/)
[![license](https://img.shields.io/badge/code-Apache--2.0-blue)](LICENSE)
[![data](https://img.shields.io/badge/data-CC--BY--4.0-blue)](LICENSE-DATA.md)

It plants known conflicts across a CRM and a document store, serves them to the agent over MCP, asks each question several times, and grades three things: was the answer right, did the agent read the sources it cites, did it refuse when no answer is justified. A question counts only when all repeats pass (`pass^k`). The gap between "right every time" and "right on average" is the finding.

![The report page: "Not reliable. Right every time on 3 of 4 questions. 1 question is never right. Trouble spot: genuine disagreement."](https://raw.githubusercontent.com/rinaldofesta/tessera/main/docs/assets/report.png)

## Sixty seconds, no key

```bash
uvx --from tessera-eval tessera report first-contact
```

That renders a committed run: Claude Sonnet 4.6 on the 4-question starter suite, 3 repeats, LLM grading with GPT-4o as the independent grader. `pass^3 75%`, mean 75%. The missing question is the one where two systems of record disagree with the same timestamp and the same authority. The only right move is to stop. The model committed a value in 3 runs of 3, each time with a rule that does not exist in the data:

| repeat | verbatim committed rationale |
|---:|---|
| 1 | "The deal desk document is the more authoritative source for contract values" |
| 2 | "the deal desk note typically reflects the most operationally reviewed figure" |
| 3 | "I'll apply the principle of preferring the deal desk document as it represents a more specific, operationally-focused record." |

Full answers and tool receipts: [`examples/first-contact-report.md`](examples/first-contact-report.md). Two more commands need no key either:

```bash
tessera compare first-contact gpt-4o --intervention model   # paired comparison, McNemar p
tessera run --model anthropic/claude-sonnet-4-6 --dry-run  # the plan, and what is missing
```

![Compare: first-contact against gpt-4o, two verdicts and two gap bars side by side, with the one-line comparability note.](https://raw.githubusercontent.com/rinaldofesta/tessera/main/docs/assets/compare.png)

Limits of that run: toy suite, n=4, and three bugs in my own harness had to go before the model's behaviour was visible. The first numbers were about Tessera.

## Your first run

```bash
uv tool install tessera-eval          # or: pipx install tessera-eval
tessera connect anthropic             # "API key:" is a hidden prompt; --key-stdin for scripts
tessera run --model anthropic/claude-sonnet-4-6
tessera ui                            # the same thing in the browser
```

There is no `--key` flag. The key goes to `~/.tessera/.env` (mode 0600, home 0700) and is never printed. `tessera run` exits 0 when the run completed, whether or not the verdict is "reliable"; exit 1 is reserved for a threshold you asked for (`--min-pass-k 0.9`).

![The Run view: the form reads "Ask claude-sonnet-4-6 the Starter questions, 3 times each."](https://raw.githubusercontent.com/rinaldofesta/tessera/main/docs/assets/run.png)

The form is a sentence. Everything else (grading engine, grader model, scaffold, seed) is under Advanced and off by default: deterministic grading, suite `starter`, 3 repeats.

## The four kinds of conflict

| the sources | right move | label in the report |
|---|---|---|
| agree | answer, from both | sources agree |
| disagree, but a rule breaks the tie (newer, more authoritative) | answer, cite both | conflict, tiebreaker applies |
| disagree with equal authority and no rule | refuse, escalate | genuine disagreement |
| do not contain the fact | refuse, do not invent it | fact missing |

`starter` has one question per kind. `meridian`, the reference suite, has 22 with at least five per kind. Every leaderboard row so far fabricated a tiebreaker on the third kind at least once; two models (claude-fable-5, claude-opus-4-8) are the first to hold that column at 100%.

## The command

| verb | what it does |
|---|---|
| `run --model M [--suite S] [--k 3] [--engine deterministic\|llm] [--min-pass-k X] [--dry-run]` | plan, then execute into `~/.tessera/runs/<id>/` |
| `report [REF\|latest\|path.eval]` | the scorecard, as Markdown |
| `history`, `archive REF [--restore]`, `import LOG` | the run folder store |
| `compare A B [--intervention model] [--require-comparable]` | paired McNemar; "protocol differs" is a finding, exit 1 only with the gate |
| `catalog [suites\|models\|providers\|scorers]` | the one vocabulary the CLI and the UI share |
| `connect PROVIDER [--key-stdin] [--base-url URL] [--test MODEL]` | store a key or a local server URL |
| `init NAME`, `validate REF` | author a suite as JSON in `~/.tessera/suites/` |
| `ui [--check]`, `guide [TOPIC]`, `leaderboard render\|extract\|verify` | the app, the built-in guide, the maintainer tooling |

Every verb but the `leaderboard` trio takes `--json` and prints one JSON object. Exit codes: 0 completed · 1 a requested gate failed · 2 provider not connected · 3 bad spec · 4 runtime error. Coding agents get the same contract in [`AGENTS.md`](AGENTS.md) and three skills under [`skills/`](skills/), both shipped in the wheel.

## Your own suite

```bash
tessera init acme-support        # writes ~/.tessera/suites/acme-support.json from a template
tessera validate acme-support    # schema + a compile in memory
tessera run --suite acme-support --model anthropic/claude-sonnet-4-6
```

In the app the same file is edited through five plain-language recipes ("a policy that changed, the old version is still on the wiki") with live validation. The JSON is yours: claims (the facts, each with its silo, timestamp and authority) and probes (the questions, with the conflict kind and the expected behaviour). Complete examples: [`examples/suites/`](examples/suites/).

## How scoring works

- **Accuracy** on the committed `ANSWER:` line (deterministic engine, `det-4`) or model-graded with an independent grader (`llm-2`). A grader equal to the model under test aborts the run.
- **Provenance** read from the agent's real MCP tool traffic, per field, credited only for data that came back, and checked against the compiled `manifest.json`. Never model-graded, in either engine.
- **Refusal** on the two kinds that demand it, with false refusal exposed on the two that do not.
- **pass^k**: a question passes only when every repeat passes. The report shows pass^k and mean side by side because a category at 0% / 67% is a different bug from one at 0% / 0%.

The standard (taxonomy, claims, probes, expected behaviour) is human-owned. The organisation on disk is generated: `python -m tessera.factory.export --seed 42` re-deals meridian's conflict graph for any seed while the category counts stay fixed, so a leaderboard can run on a withheld seed committed in advance (ADR-0008).

## Leaderboard

[`docs/leaderboard.md`](docs/leaderboard.md) is rendered from [`docs/leaderboard.rows.json`](docs/leaderboard.rows.json) and CI fails on drift. Nine rows, deterministic engine, meridian, k=3, harness disclosed per row. State of the evidence: 0 of 9 rows are backed by a committed log, so `tessera leaderboard verify` has nothing to verify yet. Backing them means re-running each model with a key; the rows stay `log: null` until that happens.

## Depth

- [`docs/reading-the-scorecard.md`](docs/reading-the-scorecard.md): the field guide to a report.
- [`docs/report.md`](docs/report.md): method, limits and measured results; [`docs/scaffold.md`](docs/scaffold.md) and [`docs/delegation.md`](docs/delegation.md): the two intervention studies.
- [`docs/adr/`](docs/adr/): fourteen decisions on record, from the response-model contract (0002) to this release (0014).
- [`docs/roadmap.md`](docs/roadmap.md) and [`docs/related-work.md`](docs/related-work.md): where it is going and where it sits among the MCP benchmarks.
- [`docs/extending-silos.md`](docs/extending-silos.md): a third silo type from your own package; [`docs/README.md`](docs/README.md) indexes the rest.
- `tessera guide`: the same material inside the terminal, five topics.

## Development

```bash
uv sync --frozen --all-extras
uv run pytest                        # the whole suite, key-free, offline, ~10 s
cd web && npm ci && npm run build    # the SPA, emitted into the package
```

CI proves, on every PR: the tests on 3.10/3.12/3.14, the web build under a 1 MB budget, no contract drift, no leaderboard drift, a wheel rebuilt from the sdist without Node that installs into an empty environment and serves the UI. House rules and the release procedure: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Integrity and limitations

- **Synthetic, public, reproducible.** No real client data enters the repository.
- **Contamination has a holdout answer.** The public blueprint is the answer key; the factory's withheld seeds are the mitigation ([ADR-0008](docs/adr/0008-scenario-factory-and-holdout-protocol.md)).
- **Documented bias.** The generator encodes assumptions about how organisations fragment knowledge. Those assumptions will be wrong in places, and they will be written down.
- **A measure under stated conditions.** A score is evidence for this suite, this model and this harness. Your organisation is a different experiment.

## Contributing

Open an issue before a large PR. The most useful contributions now: a real task where a good agent should refuse but does not, a scoring dispute with a transcript attached, and leaderboard rows with their logs under the [ADR-0006](docs/adr/0006-meridian-and-the-leaderboard-protocol.md) protocol. [Code of Conduct](CODE_OF_CONDUCT.md) · [Security policy](SECURITY.md).

## Citation

[CITATION.cff](CITATION.cff) works with GitHub's "Cite this repository" button.

```bibtex
@software{festa_tessera_2026,
  author = {Festa, Rinaldo},
  title  = {Tessera: an open methodology and generator for enterprise AI-agent reliability evals},
  year   = {2026},
  url    = {https://github.com/rinaldofesta/tessera}
}
```

## About

Built by Rinaldo Festa. I build AI agents for enterprises, then the evals that show whether they can be trusted. Build log: [rinaldofesta.com](https://rinaldofesta.com).

## License

Code: [Apache-2.0](LICENSE). Synthetic datasets (blueprints, example suites, compiled artifacts, pinned logs): [CC-BY-4.0](LICENSE-DATA.md).
