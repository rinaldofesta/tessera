# Changelog

All notable changes to Tessera are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-09-02

### Added

- A single `tessera` command with `run`, `report`, `history`, `archive`, `import`,
  `compare`, `catalog`, `connect`, `init`, `validate`, `ui`, `guide`, and
  `leaderboard render`, `leaderboard extract`, and `leaderboard verify`.
- A `~/.tessera` home for credentials, user suites, and durable folder-per-run storage.
- One ADR-0002 run payload shared by the CLI, API, and UI, with operational status,
  verdict, explicit gate result, report, receipt, diagnostics, paths, and redacted errors.
- A credential-safe catalog and offline dry-run planning before any model call.
- A three-view Run, Reports, and Connect web UI with light mode, bundled into the wheel.
- Packaging for publication on PyPI as `tessera-eval`.
- Ollama and MLX (or any OpenAI-compatible server) as first-class cards on the Connect
  page and in `tessera connect`; a `tessera guide models` topic explains the three cases.

### Changed

- Deterministic grading and the `starter` suite are now the defaults.
- `toy` is a deprecated suite alias for `starter`; the underlying protocol org remains `toy`.
- User-authored suites now live in `~/.tessera/suites`.
- The API contract is capped at 16 paths and centered on `/api/catalog` and `/api/runs`.
- `ollama/qwen3.5:latest` left the default model list; local models are typed by id.

### Removed

- The `app` optional dependency extra.
- The `tessera-variant` and `tessera-validate-transfer` console scripts.
- Separate behavior behind `tessera-report`, `tessera-leaderboard`, and `tessera-api`;
  these console scripts remain deprecated compatibility aliases for the 0.3 release.
- The experiments API and tab, standalone model-discovery and preflight endpoints, the
  in-app leaderboard and dashboard, and the raw claims editor.
- The `runs.db` store. Existing `.eval` runs can be re-imported with `tessera import`.

### Fixed

- Connecting MLX also writes the placeholder `MLX_API_KEY` that inspect_ai's
  OpenAI-compatible client requires, so MLX runs no longer fail at model initialisation.
- The stale scaffold literal that prevented the API from launching supported scaffolds.
- Import-time creation of `runs.db`.
- Default state, suite, run, environment-file, and result paths depending on the current
  working directory.

### Security

- Provider keys never appear in process arguments; `.env` is written with mode `0600`
  under a newly created `~/.tessera` home with mode `0700`.

[Unreleased]: https://github.com/rinaldofesta/tessera/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/rinaldofesta/tessera/releases/tag/v0.3.0
