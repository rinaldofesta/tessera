#!/usr/bin/env bash
# Regenerate the API contract artifacts: openapi.json + web/src/api-types.gen.ts.
# CI re-runs this and fails on `git diff` — commit both files whenever the API changes.
#
# The schema dump runs from a scratch cwd so nothing cwd-relative can leak into the
# schema. (The SPA catch-all is excluded from the schema outright — a built web/dist
# must never change openapi.json.)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

(cd "$SCRATCH" && "$PY" -c \
  "import json; from tessera.api.app import create_app; print(json.dumps(create_app().openapi(), indent=2, sort_keys=True))" \
) > "$ROOT/openapi.json"

(cd "$ROOT/web" && npm run -s gen:api)
echo "regenerated: openapi.json + web/src/api-types.gen.ts"
