#!/bin/sh

# stop on failure
set -e

. "$(dirname $0)/common.sh"

# Use C local to avoid local dates in headers
export LANG=en_US.utf8

# disable termcolor
export ANSI_COLORS_DISABLED=1

[ -z "${TMPDIR}" ] && TMPDIR="/tmp"

# do not allow undefined variables anymore
set -u
WEBOOB_TMPDIR=$(mktemp -d "${TMPDIR}/weboob_man.XXXXXX")

# path to sources
WEBOOB_DIR=$(cd $(dirname $0)/.. && pwd -P)
touch "${WEBOOB_TMPDIR}/backends"
chmod 600 "${WEBOOB_TMPDIR}/backends"
echo "file://$WEBOOB_DIR/modules" > "${WEBOOB_TMPDIR}/sources.list"

export WEBOOB_WORKDIR="${WEBOOB_TMPDIR}"
export WEBOOB_DATADIR="${WEBOOB_TMPDIR}"
export PYTHONPATH="${WEBOOB_DIR}"
# TODO can we require weboob to be installed before being able to run run_tests.sh?
# if we can, then weboob-config is present in PATH (virtualenv or whatever)
${PYTHON} -c "import sys; sys.argv='weboob-config update'.split(); from weboob.applications.weboobcfg import WeboobCfg; WeboobCfg.run()"

$PYTHON "${WEBOOB_DIR}/tools/make_man.py"

# allow failing commands past this point
STATUS=$?

rm -rf "${WEBOOB_TMPDIR}"

exit $STATUS
