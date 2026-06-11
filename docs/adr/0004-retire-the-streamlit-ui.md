# ADR-0004 — Retire the legacy Streamlit UI

- **Date**: 2026-06-11
- **Status**: Accepted

## Context

Tessera had two UIs over the same FastAPI backend: the original Streamlit
"Reliability Explorer" (`src/tessera/app/`) and the React + Vite SPA (`web/`) that
superseded it. The Streamlit app had no tests, duplicated every product surface the
SPA already covered, and `scripts/dev.sh` — the documented launch path — still
started *it* rather than the product UI. Two UIs on one API means every endpoint
change pays a double UI tax (the model-list drift that motivated ADR-0002 started
exactly there).

A retirement audit confirmed the cut is clean: nothing outside `src/tessera/app/`
imports from it (the `api_client.py` HTTP client's only consumer was the Streamlit
app itself; the SPA talks to the API via `fetch`, tests via `fastapi.testclient`),
no test references it, and CI never installs or runs it.

## Decision

Remove the Streamlit UI entirely rather than keep it as a reference:

- delete `src/tessera/app/`, the `.streamlit/` config, and `scripts/dev.sh`
  (whose sole purpose was launching API + Streamlit together);
- drop `streamlit` and `watchdog` from the `app` extra and the `tessera-app`
  console script from `pyproject.toml`;
- the launch path is the one the README documents: build `web/` once, then
  `tessera-api` serves SPA + API from a single process.

`fastapi`, `uvicorn`, `httpx`, `python-multipart`, and `python-dotenv` stay in the
`app` extra — they belong to the API side (`httpx` also backs `fastapi.testclient`
in the suite).

## Consequences

- One UI, one contract: the SPA is the only consumer of the API, and ADR-0002's
  generated types are its single source of truth.
- The git history remains the reference for the retired app; nothing dead ships in
  the package.
- Anyone with `tessera-app` in muscle memory gets a clean entry-point error after
  reinstall; the README never advertised it as the primary path.
