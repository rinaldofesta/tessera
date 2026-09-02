#!/usr/bin/env bash
# Every image the README embeds from raw.githubusercontent.com must exist in this checkout at
# the same path. Offline, so it works on a PR before the branch is merged into main.
set -euo pipefail
cd "$(dirname "$0")/.."
status=0
while IFS= read -r url; do
  path="${url#https://raw.githubusercontent.com/rinaldofesta/tessera/main/}"
  [ -f "$path" ] || { echo "MISSING $path (referenced as $url)"; status=1; }
done < <(grep -oE 'https://raw\.githubusercontent\.com/rinaldofesta/tessera/main/[^) "]+' README.md | sort -u)
exit $status
