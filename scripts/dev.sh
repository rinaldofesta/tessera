#!/usr/bin/env bash
# Start the Tessera API (uvicorn) + the Streamlit FE together. Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${TESSERA_API_PORT:-8000}"
export TESSERA_API_URL="http://127.0.0.1:${PORT}"

.venv/bin/python -m uvicorn tessera.api.app:app --host 127.0.0.1 --port "${PORT}" &
API_PID=$!
trap 'kill "${API_PID}" 2>/dev/null || true' EXIT

# wait for the API to come up
for _ in $(seq 1 30); do
  curl -sf "http://127.0.0.1:${PORT}/api/logs" >/dev/null 2>&1 && break
  sleep 0.5
done

.venv/bin/python -m streamlit run src/tessera/app/streamlit_app.py
