#!/bin/sh

# stop on failure
set -e

# path to sources
WEBOOB_DIR=$(cd $(dirname $0)/.. && pwd -P)

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
[ -z "${WEBOOB_MODULES}" ] && WEBOOB_MODULES="${WEBOOB_DIR}/modules"
[ -z "${PYTHONPATH}" ] && PYTHONPATH=""

# allow private environment setup
[ -f "${WEBOOB_WORKDIR}/pre-test.sh" ] && source "${WEBOOB_WORKDIR}/pre-test.sh"

# setup xunit reporting (buildbot slaves only)
if [ -n "${RSYNC_TARGET}" ]; then
    # by default, builder name is containing directory name
    [ -z "${BUILDER_NAME}" ] && BUILDER_NAME=$(basename $(readlink -e $(dirname $0)/../..))
else
    RSYNC_TARGET=""
fi

# find executables
if [ -z "${PYTHON}" ]; then
    which python >/dev/null 2>&1 && PYTHON=$(which python)
    which python2 >/dev/null 2>&1 && PYTHON=$(which python2)
    which python2.7 >/dev/null 2>&1 && PYTHON=$(which python2.7)
fi

if [ -z "${NOSE}" ]; then
    which nosetests >/dev/null 2>&1 && NOSE=$(which nosetests)
    which nosetests2 >/dev/null 2>&1 && NOSE=$(which nosetests2)
    which nosetests-python2.7 >/dev/null 2>&1 && NOSE=$(which nosetests-python2.7)
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
cp "${WEBOOB_BACKENDS}" "${WEBOOB_TMPDIR}/backends"

# xunit nose setup
if [ -n "${RSYNC_TARGET}" ]; then
    XUNIT_ARGS="--with-xunit --xunit-file=${WEBOOB_TMPDIR}/xunit.xml"
else
    XUNIT_ARGS=""
fi

${PYTHON} "$(dirname $0)/stale_pyc.py"

echo "file://${WEBOOB_MODULES}" > "${WEBOOB_TMPDIR}/sources.list"

export WEBOOB_WORKDIR="${WEBOOB_TMPDIR}"
export PYTHONPATH="${WEBOOB_DIR}:${PYTHONPATH}"
export NOSE_NOPATH="1"
${PYTHON} "${WEBOOB_DIR}/scripts/weboob-config" update

# allow failing commands past this point
set +e
if [ -n "${BACKEND}" ]; then
    ${PYTHON} ${NOSE} -c /dev/null -sv "${WEBOOB_MODULES}/${BACKEND}/test.py" ${XUNIT_ARGS}
    STATUS_CORE=0
else
    echo "=== Weboob ==="
    ${PYTHON} ${NOSE} -c ${WEBOOB_DIR}/setup.cfg -sv
    STATUS_CORE=$?
    echo "=== Modules ==="
    find "${WEBOOB_MODULES}" -name "test.py" | sort | xargs ${PYTHON} ${NOSE} -c /dev/null -sv ${XUNIT_ARGS}
fi
STATUS=$?

# xunit transfer
if [ -n "${RSYNC_TARGET}" ]; then
    rsync -iz "${WEBOOB_TMPDIR}/xunit.xml" "${RSYNC_TARGET}/${BUILDER_NAME}-$(date +%s).xml"
    rm "${WEBOOB_TMPDIR}/xunit.xml"
fi

# safe removal
rm -r "${WEBOOB_TMPDIR}/icons" "${WEBOOB_TMPDIR}/repositories" "${WEBOOB_TMPDIR}/modules" "${WEBOOB_TMPDIR}/keyrings"
rm "${WEBOOB_TMPDIR}/backends" "${WEBOOB_TMPDIR}/sources.list"
rmdir "${WEBOOB_TMPDIR}"

[ $STATUS_CORE -gt 0 ] && exit $STATUS_CORE
exit $STATUS
