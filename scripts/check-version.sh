#!/usr/bin/env bash
# The version is declared in three places that must agree: pyproject.toml (what PyPI
# gets), CITATION.cff (what a paper cites), src/tessera/__init__.py (what the code
# reports). A release tag, when given as $1, must match them too — release.yml passes
# the tag so a mistyped `git tag` cannot publish a mislabeled build.
set -euo pipefail
cd "$(dirname "$0")/.."

pyproject=$(sed -n 's/^version = "\([^"]*\)"/\1/p' pyproject.toml | head -1)
citation=$(sed -n 's/^version: "\([^"]*\)"/\1/p' CITATION.cff | head -1)
package=$(sed -n 's/^__version__ = "\([^"]*\)"/\1/p' src/tessera/__init__.py | head -1)

status=0
for pair in "CITATION.cff=$citation" "src/tessera/__init__.py=$package"; do
  name=${pair%%=*}; value=${pair#*=}
  if [ "$value" != "$pyproject" ]; then
    echo "version mismatch: pyproject.toml says $pyproject, $name says ${value:-<none>}" >&2
    status=1
  fi
done

if [ "${1:-}" != "" ] && [ "${1#v}" != "$pyproject" ]; then
  echo "tag $1 does not match pyproject.toml version $pyproject" >&2
  status=1
fi

[ $status -eq 0 ] && echo "version $pyproject is consistent"
exit $status
