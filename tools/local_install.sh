#!/bin/sh
set -e

if [ -z "${PYTHON}" ]; then
    which python >/dev/null 2>&1 && PYTHON=$(which python)
    which python2 >/dev/null 2>&1 && PYTHON=$(which python2)
    which python2.7 >/dev/null 2>&1 && PYTHON=$(which python2.7)
fi

exec "${PYTHON}" "$(dirname $0)/local_install.py" "$@"
