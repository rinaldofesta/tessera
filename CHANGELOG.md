# Changelog

All notable changes to Evalogy are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- The README installs `evalogy` from PyPI, where 0.3.0 was published on 2026-11-21.

## [0.3.0] - 2026-11-21

### Added

- A single `evalogy` command with `run`, `report`, `history`, `archive`, `import`,
  `compare`, `catalog`, `connect`, `init`, `validate`, `ui`, `guide`, and
  `leaderboard render`, `leaderboard extract`, and `leaderboard verify`.
- A `~/.evalogy` home for credentials, user suites, and durable folder-per-run storage.
- One ADR-0002 run payload shared by the CLI, API, and UI, with operational status,
  verdict, explicit gate result, report, receipt, diagnostics, paths, and redacted errors.
- A credential-safe catalog and offline dry-run planning before any model call.
- A three-view Run, Reports, and Connect web UI with light mode, bundled into the wheel.
- Packaging for publication on PyPI as `evalogy`.
- Ollama and MLX (or any OpenAI-compatible server) as first-class cards on the Connect
  page and in `evalogy connect`; an `evalogy guide models` topic explains the three cases.

### Changed

- The project is renamed from Tessera to Evalogy: the distribution, the command and the
  import package are `evalogy`, the home directory is `~/.evalogy` and the environment
  variables are `EVALOGY_*`. The names `tessera` and `tessera-eval` on PyPI belong to
  unrelated projects. Logs and receipts written under the old name are still read.
- Deterministic grading and the `starter` suite are now the defaults.
- `toy` is a deprecated suite alias for `starter`; the underlying protocol org remains `toy`.
- User-authored suites now live in `~/.evalogy/suites`.
- The API contract is capped at 16 paths and centered on `/api/catalog` and `/api/runs`.
- `ollama/qwen3.5:latest` left the default model list; local models are typed by id.

### Removed

- The `app` optional dependency extra.
- The `tessera-variant` and `tessera-validate-transfer` console scripts.
- Separate behavior behind the report, leaderboard and API console scripts; they remain,
  as `evalogy-report`, `evalogy-leaderboard` and `evalogy-api`, deprecated aliases of the
  single command for the 0.3 release.
- The experiments API and tab, standalone model-discovery and preflight endpoints, the
  in-app leaderboard and dashboard, and the raw claims editor.
- The `runs.db` store. Existing `.eval` runs can be re-imported with `evalogy import`.

### Fixed

- The README installs from the repository. It pointed to `tessera-eval` on PyPI, which
  is an unrelated project.
- Connecting MLX also writes the placeholder `MLX_API_KEY` that inspect_ai's
  OpenAI-compatible client requires, so MLX runs no longer fail at model initialisation.
- The stale scaffold literal that prevented the API from launching supported scaffolds.
- Import-time creation of `runs.db`.
- Default state, suite, run, environment-file, and result paths depending on the current
  working directory.

### Security

- A suite whose source name is not a safe, registered identifier is rejected when it is
  loaded. Before, a crafted name made the compiler write outside its output directory.
- The compiler refuses a link that leaves the output directory before its first write, and
  the CRM lookup and the document tools do not follow one.
- Provider keys never appear in process arguments; `.env` is written with mode `0600`
  under a newly created `~/.evalogy` home with mode `0700`.

[Unreleased]: https://github.com/rinaldofesta/evalogy/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/rinaldofesta/evalogy/releases/tag/v0.3.0
