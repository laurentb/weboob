#!/usr/bin/env bash

# Mai available environment variables
#   * RSYNC_TARGET: target on which to rsync the xunit output.
#   * XUNIT_OUT: file in which xunit output should be saved.
#   * WEBOOB_BACKENDS: path to the Weboob backends file to use.
#   * WEBOOB_CI_TARGET: URL of your Weboob-CI instance.
#   * WEBOOB_CI_ORIGIN: origin for the Weboob-CI data.

# stop on failure
set -e

. "$(dirname $0)/common.sh"

if [ -z "${PYTHON}" ]; then
    echo "Python required"
    exit 1
fi

if ! $PYTHON -c "import nose" 2>/dev/null; then
    echo "python-nose required"
    exit 1
fi

TEST_CORE=1
TEST_MODULES=1

for i in "$@"
do
case $i in
    --no-modules)
        TEST_MODULES=0
        shift
        ;;
    --no-core)
        TEST_CORE=0
        shift
        ;;
    *)
    ;;
esac
done

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
WEBOOB_TMPDIR=$(mktemp -d "${TMPDIR}/weboob_test.XXXXXX")
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

[ $VER -eq 2 ] && $PYTHON "$(dirname $0)/stale_pyc.py"

echo "file://${WEBOOB_MODULES}" > "${WEBOOB_TMPDIR}/sources.list"

export WEBOOB_WORKDIR="${WEBOOB_TMPDIR}"
export WEBOOB_DATADIR="${WEBOOB_TMPDIR}"
export PYTHONPATH="${WEBOOB_DIR}:${PYTHONPATH}"
export NOSE_NOPATH="1"

if [[ ($TEST_MODULES = 1) || (-n "${BACKEND}") ]]; then
    # TODO can we require weboob to be installed before being able to run run_tests.sh?
    # if we can, then weboob-config is present in PATH (virtualenv or whatever)
    ${PYTHON} -c "import sys; sys.argv='weboob-config update'.split(); from weboob.applications.weboobcfg import WeboobCfg; WeboobCfg.run()"
fi

# allow failing commands past this point
set +e
set -o pipefail
STATUS_CORE=0
STATUS=0
if [ -n "${BACKEND}" ]; then
    ${PYTHON} -m nose -c /dev/null --logging-level=DEBUG -sv "${WEBOOB_MODULES}/${BACKEND}/test.py" ${XUNIT_ARGS}
    STATUS=$?
else
    if [ $TEST_CORE = 1 ]; then
        echo "=== Weboob ==="
        CORE_TESTS=$(mktemp)
        ${PYTHON} -m nose --cover-package weboob -c ${WEBOOB_DIR}/setup.cfg --logging-level=DEBUG -sv 2>&1 | tee "${CORE_TESTS}"
        STATUS_CORE=$?
        CORE_STMTS=$(grep "TOTAL" ${CORE_TESTS} | awk '{ print $2; }')
        CORE_MISS=$(grep "TOTAL" ${CORE_TESTS} | awk '{ print $3; }')
        CORE_COVERAGE=$(grep "TOTAL" ${CORE_TESTS} | awk '{ print $4; }')
        rm ${CORE_TESTS}
    fi

    if [ $TEST_MODULES = 1 ]; then
        echo "=== Modules ==="
        MODULES_TESTS=$(mktemp)
        MODULES_TO_TEST=$(find "${WEBOOB_MODULES}" -name "test.py" | sort | xargs echo)
        ${PYTHON} -m nose --with-coverage --cover-package modules -c /dev/null --logging-level=DEBUG -sv ${XUNIT_ARGS} ${MODULES_TO_TEST} 2>&1 | tee ${MODULES_TESTS}
        STATUS=$?
        MODULES_STMTS=$(grep "TOTAL" ${MODULES_TESTS} | awk '{ print $2; }')
        MODULES_MISS=$(grep "TOTAL" ${MODULES_TESTS} | awk '{ print $3; }')
        MODULES_COVERAGE=$(grep "TOTAL" ${MODULES_TESTS} | awk '{ print $4; }')
        rm ${MODULES_TESTS}
    fi

    # Compute total coverage
    echo "=== Total coverage ==="
    if [ $TEST_CORE = 1 ]; then
        echo "CORE COVERAGE: ${CORE_COVERAGE}"
    fi
    if [ $TEST_MODULES = 1 ]; then
        echo "MODULES COVERAGE: ${MODULES_COVERAGE}"
    fi

    if [[ ($TEST_CORE = 1) && ($TEST_MODULES = 1) ]]; then
        TOTAL_STMTS=$((${CORE_STMTS} + ${MODULES_STMTS}))
        TOTAL_MISS=$((${CORE_MISS} + ${MODULES_MISS}))
        TOTAL_COVERAGE=$((100 * (${TOTAL_STMTS} - ${TOTAL_MISS}) / ${TOTAL_STMTS}))
        echo "TOTAL: ${TOTAL_COVERAGE}%"
    fi
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
if [[ ($TEST_MODULES = 1) || (-n "${BACKEND}") ]]; then
    rm -r "${WEBOOB_TMPDIR}/icons" "${WEBOOB_TMPDIR}/repositories" "${WEBOOB_TMPDIR}/modules" "${WEBOOB_TMPDIR}/keyrings"
fi
rm "${WEBOOB_TMPDIR}/backends" "${WEBOOB_TMPDIR}/sources.list"
rmdir "${WEBOOB_TMPDIR}"

[ $STATUS_CORE -gt 0 ] && exit $STATUS_CORE
exit $STATUS
