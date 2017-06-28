#!/bin/bash

# Mai available environment variables
#   * RSYNC_TARGET: target on which to rsync the xunit output.
#   * XUNIT_OUT: file in which xunit output should be saved.
#   * WEBOOB_BACKENDS: path to the Weboob backends file to use.
#   * WEBOOB_CI_TARGET: URL of your Weboob-CI instance.
#   * WEBOOB_CI_ORIGIN: origin for the Weboob-CI data.

# stop on failure
set -e

VER=2
if [ "$1" = -3 ]; then
	VER=3
	shift
fi

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
WEBOOB_TMPDIR=$(mktemp -d "${TMPDIR}/weboob_test.XXXXX")
[ -z "${WEBOOB_BACKENDS}" ] && WEBOOB_BACKENDS="${WEBOOB_WORKDIR}/backends"
[ -z "${WEBOOB_MODULES}" ] && WEBOOB_MODULES="${WEBOOB_DIR}/modules"
[ -z "${PYTHONPATH}" ] && PYTHONPATH=""

# allow private environment setup
[ -f "${WEBOOB_WORKDIR}/pre-test.sh" ] && source "${WEBOOB_WORKDIR}/pre-test.sh"

# setup xunit reporting (buildbot slaves only)
if [ -n "${RSYNC_TARGET}" ]; then
    # by default, builder name is containing directory name
    [ -z "${BUILDER_NAME}" ] && BUILDER_NAME=$(basename $(readlink -e $(dirname $0)/../..))
    XUNIT_OUT="${WEBOOB_TMPDIR}/xunit.xml"
else
    RSYNC_TARGET=""
fi

# Avoid undefined variables
if [ ! -n "${XUNIT_OUT}" ]; then
    XUNIT_OUT=""
fi

# Handle Weboob-CI variables
if [ -n "${WEBOOB_CI_TARGET}" ]; then
    if [ ! -n "${WEBOOB_CI_ORIGIN}" ]; then
        WEBOOB_CI_ORIGIN="Weboob unittests run"
    fi
    # Set up xunit reporting
    XUNIT_OUT="${WEBOOB_TMPDIR}/xunit.xml"
else
    WEBOOB_CI_TARGET=""
fi


# find executables
if [ -z "${PYTHON}" ]; then
    which python >/dev/null 2>&1 && PYTHON=$(which python)
    which python$VER >/dev/null 2>&1 && PYTHON=$(which python$VER)
    if [ $VER -eq 2 ]; then
        which python2.7 >/dev/null 2>&1 && PYTHON=$(which python2.7)
    else
        which python3.4 >/dev/null 2>&1 && PYTHON=$(which python3.4)
        which python3.5 >/dev/null 2>&1 && PYTHON=$(which python3.5)
        which python3.6 >/dev/null 2>&1 && PYTHON=$(which python3.6)
    fi
fi

if [ -z "${NOSE}" ]; then
    which nosetests >/dev/null 2>&1 && NOSE=$(which nosetests)
    which nosetests$VER >/dev/null 2>&1 && NOSE=$(which nosetests$VER)
    which nosetests-python$VER >/dev/null 2>&1 && NOSE=$(which nosetests-python$VER)
    if [ $VER -eq 2 ]; then
        which nosetests-python2.7 >/dev/null 2>&1 && NOSE=$(which nosetests-python2.7)
    else
        which nosetests-python3.4 >/dev/null 2>&1 && NOSE=$(which nosetests-python3.4)
        which nosetests-python3.5 >/dev/null 2>&1 && NOSE=$(which nosetests-python3.5)
        which nosetests-python3.6 >/dev/null 2>&1 && NOSE=$(which nosetests-python3.6)
    fi
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
if [ -f "${WEBOOB_BACKENDS}" ]; then
    cp "${WEBOOB_BACKENDS}" "${WEBOOB_TMPDIR}/backends"
else
    touch "${WEBOOB_TMPDIR}/backends"
    chmod go-r "${WEBOOB_TMPDIR}/backends"
fi

# xunit nose setup
if [ -n "${XUNIT_OUT}" ]; then
    XUNIT_ARGS="--with-xunit --xunit-file=${XUNIT_OUT}"
else
    XUNIT_ARGS=""
fi

${PYTHON} "$(dirname $0)/stale_pyc.py"

echo "file://${WEBOOB_MODULES}" > "${WEBOOB_TMPDIR}/sources.list"

export WEBOOB_WORKDIR="${WEBOOB_TMPDIR}"
export WEBOOB_DATADIR="${WEBOOB_TMPDIR}"
export PYTHONPATH="${WEBOOB_DIR}:${PYTHONPATH}"
export NOSE_NOPATH="1"
${PYTHON} "${WEBOOB_DIR}/scripts/weboob-config" update

# allow failing commands past this point
set +e
set -o pipefail
if [ -n "${BACKEND}" ]; then
    ${PYTHON} ${NOSE} -c /dev/null -sv "${WEBOOB_MODULES}/${BACKEND}/test.py" ${XUNIT_ARGS}
    STATUS=$?
    STATUS_CORE=0
else
    echo "=== Weboob ==="
    CORE_TESTS=$(mktemp)
    ${PYTHON} ${NOSE} --cover-package weboob -c ${WEBOOB_DIR}/setup.cfg -sv 2>&1 | tee "${CORE_TESTS}"
    STATUS_CORE=$?
    echo "=== Modules ==="
    MODULES_TESTS=$(mktemp)
    MODULES_TO_TEST=$(find "${WEBOOB_MODULES}" -name "test.py" | sort | xargs echo)
    ${PYTHON} ${NOSE} --with-coverage --cover-package modules -c /dev/null -sv ${XUNIT_ARGS} ${MODULES_TO_TEST} 2>&1 | tee ${MODULES_TESTS}
    STATUS=$?

    # Compute total coverage
    echo "=== Total coverage ==="
    CORE_STMTS=$(grep "TOTAL" ${CORE_TESTS} | awk '{ print $2; }')
    CORE_MISS=$(grep "TOTAL" ${CORE_TESTS} | awk '{ print $3; }')
    CORE_COVERAGE=$(grep "TOTAL" ${CORE_TESTS} | awk '{ print $4; }')
    MODULES_STMTS=$(grep "TOTAL" ${MODULES_TESTS} | awk '{ print $2; }')
    MODULES_MISS=$(grep "TOTAL" ${MODULES_TESTS} | awk '{ print $3; }')
    MODULES_COVERAGE=$(grep "TOTAL" ${MODULES_TESTS} | awk '{ print $4; }')
    echo "CORE COVERAGE: ${CORE_COVERAGE}"
    echo "MODULES COVERAGE: ${MODULES_COVERAGE}"
    TOTAL_STMTS=$((${CORE_STMTS} + ${MODULES_STMTS}))
    TOTAL_MISS=$((${CORE_MISS} + ${MODULES_MISS}))
    TOTAL_COVERAGE=$((100 * (${TOTAL_STMTS} - ${TOTAL_MISS}) / ${TOTAL_STMTS}))
    echo "TOTAL: ${TOTAL_COVERAGE}%"

    # removal of temp files
    rm ${CORE_TESTS}
    rm ${MODULES_TESTS}
fi

# Rsync xunit transfer
if [ -n "${RSYNC_TARGET}" ]; then
    rsync -iz "${XUNIT_OUT}" "${RSYNC_TARGET}/${BUILDER_NAME}-$(date +%s).xml"
    rm "${XUNIT_OUT}"
fi

# Weboob-CI upload
if [ -n "${WEBOOB_CI_TARGET}" ]; then
    JSON_MODULE_MATRIX=$(${PYTHON} "${WEBOOB_DIR}/tools/modules_testing_grid.py" "${XUNIT_OUT}" "${WEBOOB_CI_ORIGIN}")
    curl -H "Content-Type: application/json" --data "${JSON_MODULE_MATRIX}" "${WEBOOB_CI_TARGET}/api/v1/modules"
    rm "${XUNIT_OUT}"
fi

# safe removal
rm -r "${WEBOOB_TMPDIR}/icons" "${WEBOOB_TMPDIR}/repositories" "${WEBOOB_TMPDIR}/modules" "${WEBOOB_TMPDIR}/keyrings"
rm "${WEBOOB_TMPDIR}/backends" "${WEBOOB_TMPDIR}/sources.list"
rmdir "${WEBOOB_TMPDIR}"

[ $STATUS_CORE -gt 0 ] && exit $STATUS_CORE
exit $STATUS
