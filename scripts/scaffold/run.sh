#!/usr/bin/env bash
# Run a matrix of (seed, scaffold, model) tessera_probes evals, each in its own process
# and its own log dir under logs/scaffold/. Reads API keys from the repo .env.
# Usage:  scripts/scaffold/run.sh <seed> <scaffold> <provider/model> [<provider/model> ...]
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"
set -a; source ./.env; set +a

SEED="$1"; SCAFFOLD="$2"; shift 2
MODELS=("$@")
MANIFEST=logs/scaffold/manifest.tsv
mkdir -p logs/scaffold

for MODEL in "${MODELS[@]}"; do
  SHORT="${MODEL##*/}"
  LOGDIR="logs/scaffold/s${SEED}_${SCAFFOLD}_${SHORT}"
  rm -rf "$LOGDIR"; mkdir -p "$LOGDIR"
  OUT="/tmp/tessera/scaffold_s${SEED}_${SCAFFOLD}_${SHORT}"
  echo ">>> $(date +%H:%M:%S) seed=$SEED scaffold=$SCAFFOLD model=$MODEL"
  TESSERA_OUT="$OUT" .venv/bin/inspect eval src/tessera/evals/task.py@tessera_probes \
    --model "$MODEL" -T org=meridian -T k=3 -T seed="$SEED" -T scaffold="$SCAFFOLD" \
    --log-dir "$LOGDIR" >/dev/null 2>"$LOGDIR/stderr.txt"
  RC=$?
  EVAL=$(ls "$LOGDIR"/*.eval 2>/dev/null | head -1)
  echo "    rc=$RC log=$EVAL"
  printf "%s\t%s\t%s\t%s\t%s\n" "$SEED" "$SCAFFOLD" "$MODEL" "$RC" "$EVAL" >> "$MANIFEST"
done
echo "=== DONE seed=$SEED scaffold=$SCAFFOLD ==="
