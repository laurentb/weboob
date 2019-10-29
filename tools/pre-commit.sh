#!/usr/bin/env bash
set -eu
cd $(dirname $0)/..

./tools/run_tests.sh --no-modules

set +e
GITFILES=$({ git ls-files -m ; git diff --cached --name-only --diff-filter=ACM; }|sort -u)
if [ -n "${GITFILES}" ]; then
    GITFILES="${GITFILES}" exec ./tools/pyflakes.sh
fi
