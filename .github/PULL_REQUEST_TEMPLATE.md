## What

<!-- One paragraph: the problem and the change. Link the issue. -->

## Verification

<!-- The repo's bar: show, don't assert. Delete lines that don't apply. -->

- [ ] `.venv/bin/python -m pytest` green (key-free, ~1s) — new behavior has a test that pins it
- [ ] `cd web && npm run build` clean (if the UI changed)
- [ ] Contract regenerated **in this PR** via `bash scripts/gen-types.sh` (if any API response shape changed)
- [ ] `scorer_version` bumped + ADR proposed (if scoring semantics changed)
- [ ] No real company data, no secrets, no `.env` contents anywhere in the diff

## Protocol impact

<!-- "None" is a fine answer. If this touches the scorer, the benchmark protocol
     (ADR-0006), or meridian, say what changes for published numbers. -->
