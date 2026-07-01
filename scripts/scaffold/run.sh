#!/usr/bin/env bash
# Run a matrix of (seed, scaffold, model) tessera_probes evals, each in its own process,
# its own log dir under logs/scaffold/, and its own compiled-org dir (TESSERA_OUT) so
# parallel invocations never read each other's org. Reads API keys from the repo .env.
# Usage:  scripts/scaffold/run.sh <seed> <scaffold> <provider/model> [<provider/model> ...]
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: $0 <seed> <baseline|refusal_aware> <provider/model> [<provider/model> ...]" >&2
  exit 2
fi

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"

# Refuse to start keyless: without this check the loop below would rm -rf previously
# collected logs and then fail every eval on auth.
if [[ ! -f ./.env ]]; then
  echo "error: $REPO/.env not found (API keys) — nothing was run, no logs touched" >&2
  exit 2
fi
set -a; source ./.env; set +a

INSPECT="${INSPECT:-$REPO/.venv/bin/inspect}"   # overridable, like gen-types.sh's PYTHON

SEED="$1"; SCAFFOLD="$2"; shift 2
MANIFEST=logs/scaffold/manifest.tsv
mkdir -p logs/scaffold

for MODEL in "$@"; do
  SAFE="${MODEL//\//_}"   # keep the provider: openai/gpt-4o and azure/gpt-4o must not collide
  LOGDIR="logs/scaffold/s${SEED}_${SCAFFOLD}_${SAFE}"
  rm -rf "$LOGDIR"; mkdir -p "$LOGDIR"
  OUT="/tmp/tessera/scaffold_s${SEED}_${SCAFFOLD}_${SAFE}"
  echo ">>> $(date +%H:%M:%S) seed=$SEED scaffold=$SCAFFOLD model=$MODEL"
  RC=0
  TESSERA_OUT="$OUT" "$INSPECT" eval src/tessera/evals/task.py@tessera_probes \
    --model "$MODEL" -T org=meridian -T k=3 -T seed="$SEED" -T scaffold="$SCAFFOLD" \
    --log-dir "$LOGDIR" >/dev/null 2>"$LOGDIR/stderr.txt" || RC=$?
  EVAL="$(ls "$LOGDIR"/*.eval 2>/dev/null | head -1 || true)"
  echo "    rc=$RC log=$EVAL"
  printf "%s\t%s\t%s\t%s\t%s\n" "$SEED" "$SCAFFOLD" "$MODEL" "$RC" "$EVAL" >> "$MANIFEST"
done
echo "=== DONE seed=$SEED scaffold=$SCAFFOLD ==="
