# ADR-0016: The project is renamed Evalogy

- **Date**: 2026-11-21
- **Status**: Accepted
- **Amends**: [ADR-0014](0014-one-cli-one-home-one-payload.md)

ADR-0015 is reserved for a decision on a branch that has yet to merge.

## Context

The PyPI projects `tessera` and `tessera-eval` belong to other publishers.
The README pointed readers to another project's package. Version 0.3.0 was
never released under the old name.

## Decision

Use `evalogy` for the distribution, import package and command. Rename the
auxiliary commands, Inspect tasks, plugin group, MCP servers, web package,
environment variables and home directory in the same release. Update the
GitHub URLs, installation instructions, guides, skills, CI and citation.
Keep version 0.3.0 and the existing authorship.

Keep the original logs, leaderboard rows, public First Contact evidence,
images, study identifiers and commitments as published. Historical decisions
and study reports retain their wording. Update paths and commands needed to
use them today. Regenerate derived reports and receipts from the same logs.

## Consequences

Old logs and stored runs remain readable. New receipts use `evalogy_version`.
The command reads `EVALOGY_*` settings and uses `~/.evalogy`. It leaves
`~/.tessera` in place and performs no migration.

Screenshots in `docs/assets` still show the old name. The thesis and earlier
publications cite Tessera. Their results and provenance remain attributable
under that name.
