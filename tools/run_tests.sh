#!/bin/sh

# stop on failure
set -e

BACKEND="${1}"
if [ -z "${WEBOOB_WORKDIR}" ]; then
    # use the old workdir by default
    WEBOOB_WORKDIR="${HOME}/.weboob"
    # but if we can find a valid xdg workdir, switch to it
    [ "${XDG_CONFIG_HOME}" != "" ] || XDG_CONFIG_HOME="${HOME}/.config"
    [ -d "${XDG_CONFIG_HOME}/weboob" ] && WEBOOB_WORKDIR="${XDG_CONFIG_HOME}/weboob"
fi
[ -z "${TMPDIR}" ] && TMPDIR="/tmp"
[ -z "${WEBOOB_BACKENDS}" ] && WEBOOB_BACKENDS="${WEBOOB_WORKDIR}/backends"

# find executables
if [ -z "${PYTHON}" ]; then
    which python >/dev/null 2>&1 && PYTHON=$(which python)
    which python2 >/dev/null 2>&1 && PYTHON=$(which python2)
fi

if [ -z "${NOSE}" ]; then
    which nosetests >/dev/null 2>&1 && NOSE=$(which nosetests)
    which nosetests2 >/dev/null 2>&1 && NOSE=$(which nosetests2)
fi

if [ -z "${PYTHON}" ]; then
    echo "Python required"
    exit 1
fi

if [ -z "${NOSE}" ]; then
    echo "python-nose required"
    exit 1
fi

# do not allow undefined variables anymore
set -u
WEBOOB_TMPDIR=$(mktemp -d "${TMPDIR}/weboob_test.XXXXX")
cp "${WEBOOB_BACKENDS}" "${WEBOOB_TMPDIR}/"

# path to sources
WEBOOB_DIR=$(readlink -e $(dirname $0)/..)
find $WEBOOB_DIR -name "*.pyc" -delete
echo "file://$WEBOOB_DIR/modules" > "${WEBOOB_TMPDIR}/sources.list"

export WEBOOB_WORKDIR="${WEBOOB_TMPDIR}"
export PYTHONPATH="${WEBOOB_DIR}"
${PYTHON} "${WEBOOB_DIR}/scripts/weboob-config" update

# allow failing commands past this point
set +e
if [ -n "${BACKEND}" ]; then
    ${PYTHON} ${NOSE} -sv "${WEBOOB_DIR}/modules/${BACKEND}"
else
    find "${WEBOOB_DIR}/weboob" "${WEBOOB_DIR}/modules" -name "test.py" | xargs ${PYTHON} ${NOSE} -sv
fi
STATUS=$?

# safe removal
rm -r "${WEBOOB_TMPDIR}/icons" "${WEBOOB_TMPDIR}/repositories" "${WEBOOB_TMPDIR}/modules" "${WEBOOB_TMPDIR}/keyrings"
rm "${WEBOOB_TMPDIR}/backends" "${WEBOOB_TMPDIR}/sources.list"
rmdir "${WEBOOB_TMPDIR}"

exit $STATUS
