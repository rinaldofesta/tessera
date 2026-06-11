# ADR-0002 — Pydantic response models are the API contract

- **Date**: 2026-06-11
- **Status**: Accepted

## Context

The React SPA's TypeScript types were written by hand against what the FastAPI
endpoints happened to return. They drifted: an audit found `LogMeta` missing its
`path` field, and the model list was duplicated between the SPA and the Streamlit
app. Nothing failed when the API and the UI disagreed — the lie surfaced only at
runtime, if at all.

## Decision

One contract, single-sourced from the API, enforced in both directions:

1. **Every JSON route declares a `response_model`** (`src/tessera/api/responses.py`).
   A meta-test walks the route table and fails if a route lacks one (SSE exempt).
2. FastAPI **validates every response** against its model — so the existing key-free
   test suite doubles as a contract test suite for free.
3. The OpenAPI schema is **committed** (`openapi.json`) and `openapi-typescript`
   generates `web/src/api-types.gen.ts` from it (`bash scripts/gen-types.sh`).
   `web/src/types.ts` declares nothing by hand — it is a pure alias layer over the
   generated schemas.
4. A CI `contract` job regenerates both files and **fails on drift**
   (`git diff --exit-code`). fastapi/pydantic are pinned in that job because schema
   emission shifts across minor versions; bumping those pins and regenerating the
   contract must happen in the same commit.

## Consequences

- A shape change that isn't reflected end-to-end cannot merge: either a response
  fails validation in tests, or the generated types drift and CI fails.
- The generation dump must run from a scratch cwd — importing the app writes
  `runs.db`, and a local `web/dist` adds the SPA catch-all route CI lacks.
- Pydantic never emits `default` for `default_factory` fields, so list fields arrive
  optional in the generated TS; consumers normalize at the boundary (`?? []`) —
  honest, since they are optional on authoring input.
- The first run of the net caught a real bug: a test fixture storing a partial
  report shape that production code never produced.
