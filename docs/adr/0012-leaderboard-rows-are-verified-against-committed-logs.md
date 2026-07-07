# ADR-0012 — Leaderboard rows are verified against committed logs

- **Date**: 2026-07-07
- **Status**: Accepted
- **Extends**: ADR-0006 (meridian + the leaderboard protocol)
- **Refines**: ADR-0010 (the leaderboard is generated from a manifest)

## Context

ADR-0010 made the leaderboard a deterministic render of a committed manifest and enforced
that render in CI, but it drew an explicit line: *"The manifest guarantees integrity of
rendering, not provenance of numbers: a value hand-entered into the JSON is still trusted.
Provenance is A3's job."* It also introduced a per-row `log` field as the bridge to that
work. This ADR is A3: it delivers the provenance guarantee.

The gap it closes: today a maintainer could type any number into `leaderboard.rows.json`,
and CI would render it faithfully and pass. Nothing tied a row's numbers to a real run.

## Decision

A row may be **backed** by its Inspect `.eval` log, committed to the repo, and CI
re-derives the row from that log.

1. **The `log` field is `null` or `{"path": "<repo-relative>", "sha256": "<hex>"}`.** This
   refines ADR-0010, which described `log` as a bare digest — a digest alone cannot be
   located, so CI could not verify it. The path locates the committed log; the sha256 pins
   its bytes.
2. **Committed leaderboard logs live under `logs/leaderboard/`**, gitignore-negated exactly
   like the ADR-0008 holdout `COMMITMENT.json`/`REVEAL.json`. Inspect logs are ~130 KB, so
   the cost is small.
3. **`tessera-leaderboard --extract <log>` stamps a repo-relative path** (resolved against
   the `.git` root, independent of the cwd it was run from) plus the sha256.
4. **`tessera-leaderboard --manifest … --verify`** — for every row with a non-null `log`:
   reject an unsafe path (absolute, drive-letter, backslash, or `..` escape) before touching
   the filesystem; check the file exists and its sha256 matches; then **re-derive the row
   from the log** and assert the log-derived fields reproduce the manifest's. A row with
   `log: null` is reported as *unbacked*, not a failure.
5. **CI runs `--verify`.** Verification failure exits **2** (the same code as an argparse
   usage error — CI only distinguishes zero from non-zero; the specific cause is on stderr).

The comparison respects two boundaries. It compares only the **log-derived fields**
(`model`, `date`, `scorer_version`, `org`, `k`, `scaffold`, `seed`, `harness`, and the
rates) — never `label`, `notes`, or `log`, which are maintainer metadata; a hand-edited
label must not fail verification. And rates are compared by their **rendered value**
(`_pct`), so a manifest's display-rounded `0.667` matches a log's exact `2/3`: "backed"
means "reproduces the published cell", not bit-equality.

## Consequences

- The ADR-0010 consequence "Provenance is A3's job" is now **delivered**: a backed row's
  numbers are provably a real run's output, checked in CI on every push.
- The rollout is a ratchet. All rows ship `log: null` today (the frontier-model runs are not
  yet committed), so `--verify` is a passing no-op that reports coverage (`0/9 backed`). The
  moment a real log is committed and its row references it, CI enforces that row forever.
- `--verify` is safe to run on untrusted PRs: it reads bytes only at strictly repo-relative
  paths, so a manifest cannot point it at `/etc/passwd` or `../../secret`.
- Backing the eight current rows is follow-up work for whoever holds the logs; the mechanism
  and the maintainer flow (`logs/leaderboard/README.md`) are in place.
