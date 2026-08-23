# Contributing to Tessera

Thank you for considering it. Tessera measures whether AI agents can be trusted on
fragmented enterprise knowledge — so the bar for its own code is the same one it
holds agents to: **verified, traceable, honest about limitations.** This guide tells
you how to contribute without fighting the repo.

## TL;DR

```bash
git clone https://github.com/rinaldofesta/tessera && cd tessera
python -m venv .venv && .venv/bin/pip install -e ".[dev,app]"
.venv/bin/python -m pytest          # the whole suite: key-free and offline
```

If those tests pass, you have everything you need — **no API key is required to
develop here.** Open an issue before a large PR.

## What is most useful right now

In order:

1. **A real enterprise reasoning task where good agents should refuse but do not.**
   The unresolvable-tie fabrication is the headline finding; more shapes of it make
   the benchmark stronger. Use the *new org / dataset proposal* issue template.
2. **Critiques of the metric definitions** — especially provenance and refusal
   scoring. If you believe a grade is wrong, use the *scoring dispute* issue
   template with a transcript: the scorer's verdicts are adjudicated from evidence,
   and documented limitations (see the bottom of `src/tessera/evals/scoring.py`)
   are revisited when the evidence shows they bite real behavior.
3. **Realistic fragmentation patterns** the generator should model (how knowledge
   actually scatters and contradicts itself across CRMs, wikis, tickets).
4. **Leaderboard rows**: a meridian run on a model we have not measured, under the
   exact protocol (`det`, `k=3`, full 22 probes, the **baseline scaffold** —
   `-T scaffold=baseline`, the default; the refusal-aware arm of ADR-0009 is an
   intervention study, never a leaderboard row — see
   [docs/adr/0006](docs/adr/0006-meridian-and-the-leaderboard-protocol.md)).
   Every 0/3 probe gets adjudicated from its transcript before the row ships. The table
   itself is generated — never hand-edit `docs/leaderboard.md`: commit the run's `.eval`
   under `logs/leaderboard/`, run `tessera-leaderboard --extract logs/leaderboard/<run>.eval`
   to get the row's JSON (its `log` stamped `{path, sha256}`), merge it into
   `docs/leaderboard.rows.json`, regenerate with `--manifest`, and confirm with `--verify`.
   CI fails on drift (ADR-0010) and re-derives every log-backed row from its committed log
   (ADR-0012). A row with `log: null` is allowed but unbacked — attach the log to make it
   verifiable.

## Development setup

- Python ≥ 3.10 (CI runs the suite + a web build + a contract-drift check).
- `pip install -e ".[dev,app]"` gives you the eval, the report CLIs
  (`tessera-report`, `tessera-leaderboard`, `tessera-validate-transfer`) and the FastAPI/SPA product
  (`tessera-api`).
- The web UI lives in `web/` (React + Vite + TS): `cd web && npm install && npm run build`.
- A live eval run is the only thing that needs keys: put `ANTHROPIC_API_KEY` /
  `OPENAI_API_KEY` in `.env` (gitignored), then
  `inspect eval src/tessera/evals/task.py@tessera_probes -T org=toy -T judge=deterministic -T k=2`.

## House rules (the ones that will bite you if skipped)

These are decisions on record in [`docs/adr/`](docs/adr/) — one file per decision.
Read the index before changing anything load-bearing.

- **Tests first, key-free always.** The suite runs offline: scorer engines
  are stubbed, Inspect logs are fabricated in-memory. A new feature lands with the
  test that pins it. Each test file is self-contained (no cross-test-file imports —
  CI cannot resolve them).
- **`k` lives in the task** (ADR-0001). Never pass eval-level `epochs`; the task
  owns both the count and the `pass_k` reducer.
- **Response models are the contract** (ADR-0002). If you change an API response
  shape, regenerate the contract **in the same commit**:
  `bash scripts/gen-types.sh` (updates `openapi.json` + `web/src/api-types.gen.ts`).
  The CI `contract` job fails on drift. The fastapi/pydantic pins in that job move
  only together with a regeneration.
- **Scorer changes bump `scorer_version`** (ADR-0003/0005). Scoring semantics are
  versioned (`det-4` / `llm-2` today); reports publish the version per row and
  trend comparisons partition on it. A semantics change without a bump corrupts
  every published number.
- **Purity invariants are tested.** `src/tessera/report/` modules must not import
  `inspect_ai` (only `log_adapter.py` and `cli.py` may — there is a test that
  parses the AST). The compiler is deterministic and pure.
- **The benchmark protocol is frozen per row** (ADR-0006): deterministic engine,
  k=3, full probe set, the baseline scaffold, the authored org (seed 0), no
  model-specific prompt tuning. Comparability guards are executable —
  `tessera-leaderboard` refuses mixed scorer_version/org/k/scaffold/seed.
- **`harness` is a displayed axis, not a guard** (ADR-0011): it labels how a row's
  model calls were dispatched. Canonical values are **`single`** (a lone model — the
  default, and what every `tessera_probes` run is) and **`ensemble`** (a multi-agent
  configuration). Use exactly those two strings, not `moa`/`MoA`/etc. An ensemble ranks
  in the table only if it still matches every guarded dimension; it is shown with the
  `harness` column disclosed.

## Adding an org / dataset

An org is a **Blueprint**: claims (atomic facts, one per silo) + probes (questions
with expected behavior). Start from `src/tessera/examples/your_org.py` (the starter
template) or `src/tessera/examples/meridian_org.py` (the gold standard: ≥5 probes per conflict
type, both resolution rules, authority probes where the binding doc is *older* than
the CRM row, anti-prior values, no template shortcuts). Offline gates in
`tests/test_meridian_org.py` show what a benchmark-grade org must pin. Validators
in `src/tessera/models.py` enforce coherence (refuse ⇒ no answer, resolvable ⇒
resolution_rule, void ⇒ no references).

## Pull requests

- Open an issue first for anything beyond a small fix.
- One topic per PR; conventional-commit style messages
  (`feat(evals): …`, `fix(report): …`).
- Before pushing: `.venv/bin/python -m pytest` green, `cd web && npm run build`
  clean if you touched the UI, contract regenerated if you touched response models.
- CI must be green (`tests`, `web`, `quickstart`, `contract`, `leaderboard`). PRs from forks run the same jobs;
  all key-free.
- If your change alters scoring or the protocol, say so loudly in the PR body and
  propose the ADR. Decisions get recorded; surprises do not.

## Reporting

- **Bugs / wrong grades**: use the issue templates — a scoring dispute with a
  transcript is a first-class contribution, not a complaint.
- **Security**: see [SECURITY.md](SECURITY.md) — do not open a public issue.
- **Conduct**: see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License of contributions

Code contributions are accepted under [Apache-2.0](LICENSE); dataset contributions
under [CC-BY-4.0](LICENSE-DATA.md). By submitting a PR you license your
contribution under those terms and represent that you have the right to do so
(no CLA).
