# ADR-0010 — The leaderboard is generated from a committed manifest

- **Date**: 2026-07-07
- **Status**: Accepted
- **Extends**: ADR-0006 (meridian + the leaderboard protocol)

## Context

`docs/leaderboard.md` is the flagship artifact, and it was unverifiable. It is rendered
from `.eval` logs by `tessera-leaderboard`, but the logs are gitignored, so nobody — not
a reviewer, not CI — could reproduce the table. PR #16 added four rows (Fable 5, Opus 4.8,
Sonnet 5, and a MoA ensemble) by **hand-editing the Markdown**: the ADR-0006 comparability
guard in `leaderboard.py` never ran, no logs were committed, and the ensemble row — a
scaffold-level intervention — landed ranked among single-model baseline rows where the
guard, which only sees `scaffold=baseline` from the shim, cannot detect it. Anyone could
type any number into the table and nothing would fail.

## Decision

The Markdown is a **deterministic render of a committed manifest**, enforced by CI — the
same single-source-plus-drift-gate pattern as the API contract (ADR-0002).

1. **`docs/leaderboard.rows.json` is the source of truth.** It holds `rows` (ranked
   baseline entries, each exactly a `leaderboard_rows()`-shaped dict plus an optional
   `log`) and `exhibitions` (unranked out-of-protocol configurations). It is small,
   reviewable, and hand-editable — the Markdown is not.
2. **`render_manifest(manifest)` renders the table**; the ADR-0006 uniformity guard runs
   on `rows` regardless of whether they arrive from logs or the manifest. Exhibitions are
   out-of-protocol by definition and bypass the guard, rendered in their own section.
3. **`tessera-leaderboard --extract <log>` emits a row's JSON**, stamped with the log's
   sha256, so a row's numbers are guaranteed to match a real run. `--manifest` renders the
   Markdown from the manifest — no logs needed.
4. **A CI `leaderboard` job regenerates `docs/leaderboard.md` from the manifest and fails
   on drift** (`git diff --exit-code`). A hand-typed table cell, or a manifest that
   violates the comparability guard (render exits non-zero), fails the build.

## Consequences

- The table can no longer be edited by hand and merged; it is always `render_manifest`
  of the committed manifest. A keystone test pins the byte-for-byte equality directly.
- The four PR #16 rows and the MoA exhibition are represented as manifest data with
  `log: null` — honest about the fact that their logs are not yet committed. The `log`
  field is the bridge to archiving regenerable logs (roadmap A3), where CI will be able
  to verify a committed log against its digest.
- The manifest guarantees *integrity of rendering*, not *provenance of numbers*: a value
  hand-entered into the JSON is still trusted. Provenance is A3's job; ADR-0010 only
  removes the hand-edited-Markdown failure mode.
- The MoA ensemble stays visible but unranked, in an "Out-of-protocol exhibitions"
  section, until a `harness` comparability dimension (a future ADR) lets ensembles be
  guarded and rejoin the ranked table.
