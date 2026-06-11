#!/usr/bin/env bash
# Regenerate the API contract artifacts: openapi.json + web/src/api-types.gen.ts.
# CI re-runs this and fails on `git diff` — commit both files whenever the API changes.
#
# The schema dump runs from a scratch cwd, never the repo root: importing
# tessera.api.app creates runs.db relative to cwd (module-level create_app()), and a
# web/dist present at cwd would add the SPA catch-all route to the schema — a route a
# fresh CI checkout doesn't have, i.e. guaranteed false drift.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

(cd "$SCRATCH" && "$PY" -c \
  "import json; from tessera.api.app import create_app; print(json.dumps(create_app().openapi(), indent=2))" \
) > "$ROOT/openapi.json"

(cd "$ROOT/web" && npm run -s gen:api)
echo "regenerated: openapi.json + web/src/api-types.gen.ts"
