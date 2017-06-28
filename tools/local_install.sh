#!/bin/sh
set -e

. "$(dirname $0)/common.sh"

$PYTHON "$(dirname $0)/stale_pyc.py"

exec $PYTHON "$(dirname $0)/local_install.py" "$@"
