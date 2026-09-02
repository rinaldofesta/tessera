#!/usr/bin/env bash
# Prove that the shipped sdist can rebuild a wheel whose command surface and bundled
# UI work from an empty environment, away from the source checkout. Only the caller
# without a Node toolchain on PATH (ci.yml's `build` job) additionally proves the
# rebuild needs no Node; release.yml's `build` job runs actions/setup-node first, so
# it does not enforce that particular guarantee.
set -euo pipefail

# Resolve a relative dist_dir against the caller's cwd before we cd to the repo root.
dist_dir=${1:-dist}
case "$dist_dir" in
  /*) ;;
  *) dist_dir="$PWD/$dist_dir" ;;
esac
cd "$(dirname "$0")/.."

shopt -s nullglob
sdists=("$dist_dir"/*.tar.gz)
if [ "${#sdists[@]}" -ne 1 ]; then
  echo "expected exactly one sdist in $dist_dir, found ${#sdists[@]}" >&2
  exit 1
fi

work=$(mktemp -d)
tar -xzf "${sdists[0]}" -C "$work"
sources=("$work"/*)
if [ "${#sources[@]}" -ne 1 ] || [ ! -d "${sources[0]}" ]; then
  echo "expected the sdist to contain exactly one source directory" >&2
  exit 1
fi

source_dir=${sources[0]}
(cd "$source_dir" && uv build --wheel --out-dir "$work/dist")
wheels=("$work"/dist/*.whl)
if [ "${#wheels[@]}" -ne 1 ]; then
  echo "expected exactly one wheel in $work/dist, found ${#wheels[@]}" >&2
  exit 1
fi

uv venv "$work/venv" --python 3.12
uv pip install --python "$work/venv/bin/python" "${wheels[0]}"

smoke_dir=$(mktemp -d)
cd "$smoke_dir"
export TESSERA_HOME
TESSERA_HOME=$(mktemp -d)
T="$work/venv/bin/tessera"

"$T" ui --check
"$T" report first-contact --json \
  | "$work/venv/bin/python" -c "import json,sys; d=json.load(sys.stdin); assert d['verdict']['pass_k_rate']==0.75"

# Capture before grep: under pipefail, grep -q may close a producer's pipe early.
guide_list=$("$T" guide --list)
grep -q start <<<"$guide_list"
wheel_list=$(unzip -l "${wheels[0]}")
grep -q 'tessera/data/web/index.html' <<<"$wheel_list"
