# ADR-0014 — One CLI, one home, one payload

- **Date**: 2026-09-02
- **Status**: Accepted
- **Extends**: ADR-0002 (response models are the contract)

## Context

Tessera's product surface had grown into five scripts, twelve overlapping concepts, two
run stores, and paths whose meaning changed with the current working directory. The web
application and command-line tools used different launch and storage vocabulary. There was
no installable PyPI release, so the supported product was not clear from the package alone.

That fragmentation made simple questions hard to answer: which command starts a run, where
the result is durable, which response represents it, and whether a successful operation
means a reliable model. It also made release evidence weaker because different entry points
could exercise different artifacts.

## Decision

1. **One command.** `src/tessera/cli.py` owns the supported `tessera` command and its verbs.
   The old report, leaderboard, and API names are temporary deprecated aliases; the variant
   and transfer scripts are removed.
2. **One home and folder store.** `src/tessera/paths.py` resolves state under `~/.tessera`
   (or `TESSERA_HOME`), with user suites in `suites/` and one directory per run in `runs/`.
   `src/tessera/store.py` defines the durability contract: atomic sibling writes followed by
   rename and directory fsync, per-run locked transitions, artifacts before the final
   `run.json`, and reconciliation of interrupted work. A completed state therefore implies
   its artifacts are present.
3. **One run payload.** `src/tessera/contract.py` and `src/tessera/runner.py` define the
   ADR-0002 payload used by CLI, API, and UI. `ok` reports operational completion, never
   reliability; `verdict` carries reliability, while requested thresholds appear as an
   explicit `gate` and have their own exit status.
4. **One vocabulary.** `src/tessera/catalog.py` is the only catalog for suites, models,
   providers, scorers, scaffolds, and defaults. Both `tessera catalog` and
   `/api/catalog` expose it, and dry-run planning resolves requests through it.
5. **Defaults change without changing the protocol identity.** The default engine is
   `deterministic` and the default suite name is `starter`. `toy` remains a deprecated alias,
   while `starter` still maps to the protocol org id `toy`; historical and comparable run
   identities do not get silently renamed.
6. **The product surface is cut to what the command uses.** The API is bounded to 16 paths
   around catalog, planning, runs, suites, providers, and comparisons. Experiments, model
   discovery, standalone preflight, and in-app leaderboard endpoints are removed. The web
   UI is Run, Reports, and Connect; experiments, dashboard, and leaderboard views are cut.
7. **One distribution.** The PyPI project is `tessera-eval`, and the wheel contains the web
   bundle and the `tessera` entry point.
8. **Secrets do not enter argv.** `tessera connect` accepts keys through a hidden prompt or
   `--key-stdin`; `src/tessera/env_writer.py` persists them to the protected home file.

## Consequences

- This is a breaking release: old stores, scripts, endpoint names, and UI bookmarks are not
  the supported surface. The three compatibility aliases give callers one release to move
  to `tessera report`, `tessera leaderboard`, and `tessera ui`.
- Existing raw Inspect logs remain usable through `tessera import`; `runs.db` is not migrated.
- CI now proves that versions agree, tests pass on the supported Python range, the web bundle
  builds, contracts and generated leaderboard material do not drift, and backed leaderboard
  rows reproduce their committed logs.
- The release workflow additionally proves that a pushed tag matches the declared version,
  the sdist can rebuild an installable wheel, the wheel works in an empty environment with
  its UI bundle, and the checked `dist` artifacts are the ones attached to the GitHub Release
  or explicitly published through the protected PyPI environment.
- PyPI publication cannot follow a tag automatically: it requires a manual dispatch with
  `publish_pypi=true`, trusted publishing, and the repository's `pypi` environment review.

## Relationship to earlier decisions

- **ADR-0002:** the response-model contract remains; this ADR makes its run envelope the
  shared payload across every supported surface.
- **ADR-0006:** deterministic grading becomes the product default, while the Meridian
  leaderboard protocol and the internal `toy` protocol identifier remain unchanged.
- **ADR-0010:** the committed manifest remains the leaderboard source; its tooling moves
  under `tessera leaderboard` rather than remaining an application view.
- **ADR-0012:** committed-log verification remains the provenance gate and is exercised by
  CI through the consolidated command.
