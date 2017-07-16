#!/bin/bash -u
. "$(dirname $0)/common.sh"

find_cmd () {
    for cmd in $@; do
        which $cmd 2>/dev/null && return
    done
    return 1
}

PY3MODS=./tools/py3-compatible.modules

cd $(dirname $0)/..

MODULE_FILES=$(git ls-files|grep '^modules/.*\.py$')
MODULE_FILES3=$(printf "%s\n" $MODULE_FILES|grep -F -f $PY3MODS)

PYFILES=$(git ls-files | grep '^scripts\|\.py$'|grep -v boilerplate_data|grep -v '^modules'|grep -v '^contrib')
PYFILES3="$(printf "%s\n" $PYFILES | grep -v /deprecated/) $MODULE_FILES3"
PYFILES="$PYFILES $MODULE_FILES"
grep -n 'class [^( ]\+:$' ${PYFILES} && echo 'Error: old class style found, always inherit object' && exit 3
grep -n $'\t\|\s$' ${PYFILES} && echo 'Error: tabs or trailing whitespace found, remove them' && exit 4
grep -Fn '.setlocale' ${PYFILES} && echo 'Error: do not use setlocale' && exit 5
grep -Fn '__future__ import with_statement' ${PYFILES} && echo 'Error: with_statement useless as we do not support Python 2.5' &&  exit 6
grep -nE '^[[:space:]]+except [[:alnum:] ]+,[[:alnum:] ]+' ${PYFILES} && echo 'Error: use new "as" way of naming exceptions' && exit 7
grep -nE "^ *print " ${PYFILES} && echo 'Error: Use the print function' && exit 8
grep -Fn ".has_key" ${PYFILES} && echo 'Error: Deprecated, use operator "in"' && exit 9
grep -Fn "os.isatty" ${PYFILES} && echo 'Error: Use stream.isatty() instead of os.isatty(stream.fileno())' && exit 10
grep -Fn "raise StopIteration" ${PYFILES} && echo 'Error: PEP 479' && exit 11

grep -nE "\.iter(keys|values|items)\(\)" ${PYFILES3} | grep -Fv "six.iter" && echo 'Error: iterkeys/itervalues/iteritems is forbidden' && exit 12

grep -nE "^ *print(\(| )" ${MODULE_FILES} && echo 'Error: Use of print in modules is forbidden, use logger instead' && exit 20
grep -n xrange ${MODULE_FILES3} && echo 'Error: xrange is forbidden' && exit 21
grep -nE "from (urllib|urlparse) import" ${MODULE_FILES3} && echo 'Error: python2 urllib is forbidden' && exit 22
grep -nE "import (urllib|urlparse)$" ${MODULE_FILES3} && echo 'Error: python2 urllib is forbidden' && exit 22


if ${PYTHON2} -c "import flake8" 2>/dev/null; then
    FLAKER2=flake8
    OPT2="--select=E9,F"
elif ${PYTHON2} -c "import pyflakes" 2>/dev/null; then
    FLAKER2=pyflakes
    OPT2=
else
    echo "flake8 or pyflakes for python2 not found"
    exit 1
fi

if ${PYTHON3} -c "import flake8" 2>/dev/null; then
    FLAKER3=flake8
    OPT3="--select=E9,F"
elif ${PYTHON3} -c "import pyflakes" 2>/dev/null; then
    FLAKER3=pyflakes
    OPT3=
else
    echo "flake8 or pyflakes for python3 not found"
    exit 1
fi

$PYTHON2 -m ${FLAKER2} ${OPT2} ${PYFILES} || exit 32
$PYTHON3 -m ${FLAKER3} ${OPT3} ${PYFILES3} || exit 33

exit 0
