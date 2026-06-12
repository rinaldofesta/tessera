# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

- Preferred: [GitHub private vulnerability reporting](https://github.com/rinaldofesta/tessera/security/advisories/new)
  ("Report a vulnerability" on the repo's Security tab).
- Or email **festarinaldo@gmail.com** with `[tessera security]` in the subject.

You will get an acknowledgment within a few days. Please include reproduction
steps; a failing test is the best report.

## Scope worth knowing about

Tessera is a **local-first** tool: the FastAPI server (`tessera-api`) binds
locally, serves the SPA from `web/dist`, and is not hardened for public exposure —
do not put it on the open internet. Things we do treat as vulnerabilities:

- path traversal or file access outside the repo through the API
  (org names are validated — see commit `9a9e637` for precedent);
- anything that lets a blueprint or eval log execute code at compile/report time
  (the compiler and report layer are pure by design);
- secrets leaking into logs, reports, or compiled artifacts (`.env` keys must
  never appear in `.eval` files or scorecards).

## Supported versions

Pre-1.0: only the latest `main` is supported. Fixes land there.
