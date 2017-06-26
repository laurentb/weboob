#!/bin/sh

# stop on failure
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

[ -z "${TMPDIR}" ] && TMPDIR="/tmp"

# do not allow undefined variables anymore
set -u
WEBOOB_TMPDIR=$(mktemp -d "${TMPDIR}/weboob_lint.XXXXX")

# path to sources
WEBOOB_DIR=$(cd $(dirname $0)/.. && pwd -P)
touch "${WEBOOB_TMPDIR}/backends"
chmod 600 "${WEBOOB_TMPDIR}/backends"
echo "file://$WEBOOB_DIR/modules" > "${WEBOOB_TMPDIR}/sources.list"

export WEBOOB_WORKDIR="${WEBOOB_TMPDIR}"
export WEBOOB_DATADIR="${WEBOOB_TMPDIR}"
export PYTHONPATH="${WEBOOB_DIR}"
$PYTHON "${WEBOOB_DIR}/scripts/weboob-config" update

$PYTHON "${WEBOOB_DIR}/tools/weboob_lint.py"

# allow failing commands past this point
STATUS=$?

rm -rf "${WEBOOB_TMPDIR}"

exit $STATUS
