#!/bin/bash
# stop on failure
set -e
BACKEND="${1}"
[ "${WEBOOB_WORKDIR}" != "" ] || WEBOOB_WORKDIR="${HOME}/.weboob"
[ "${TMPDIR}" != "" ] || TMPDIR="/tmp"

# do not allow undefined variables anymore
set -u
WEBOOB_TMPDIR=$(mktemp -d "${TMPDIR}/weboob_test.XXXXX")
cp "${WEBOOB_WORKDIR}/backends" "${WEBOOB_TMPDIR}/"

WEBOOB_DIR=$(readlink -e $(dirname $0)/..)
echo "file://$WEBOOB_DIR/modules" > "${WEBOOB_TMPDIR}/sources.list"

export WEBOOB_WORKDIR="${WEBOOB_TMPDIR}"
"${WEBOOB_DIR}/scripts/weboob-config" update

# allow failing commands past this point
set +e
if [ "${BACKEND}" != "" ]; then
    nosetests -sv "${WEBOOB_DIR}/modules/${BACKEND}"
else
    find "${WEBOOB_DIR}/weboob" "${WEBOOB_DIR}/modules" -name test.py | xargs nosetests -sv
fi

# safe removal
rm -r "${WEBOOB_TMPDIR}"/{icons,repositories,modules}
rm "${WEBOOB_TMPDIR}"/{backends,sources.list}
rmdir "${WEBOOB_TMPDIR}"
