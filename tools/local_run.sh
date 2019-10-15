#!/bin/sh
set -e

. "$(dirname $0)/common.sh"

[ $VER -eq 2 ] && $PYTHON "$(dirname $0)/stale_pyc.py"

exec $PYTHON "$(dirname $0)/local_run.py" "$@"
