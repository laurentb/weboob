#!/bin/sh
set -e

VER=2
if [ "$1" = -3 ]; then
    VER=3
    shift
fi

if [ -z "${PYTHON}" ]; then
    which python >/dev/null 2>&1 && PYTHON=$(which python)
    which python$VER >/dev/null 2>&1 && PYTHON=$(which python$VER)
    if [ $VER -eq 2 ]; then
        which python2.7 >/dev/null 2>&1 && PYTHON=$(which python2.7)
    else
        which python3.4 >/dev/null 2>&1 && PYTHON=$(which python3.4)
    fi
fi

$PYTHON "$(dirname $0)/stale_pyc.py"

exec $PYTHON "$(dirname $0)/local_install.py" "$@"
