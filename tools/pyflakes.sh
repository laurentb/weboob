#!/bin/bash -u

VER=2
if [ "${1-}" = -3 ]; then
    VER=3
    shift
fi

cd $(dirname $0)
cd ..
PYFILES=$(git ls-files|grep '^scripts\|\.py$'|grep -v boilerplate_data|tr '\n' ' ')
grep -n 'class [^( ]\+:$' ${PYFILES} && echo 'Error: old class style found, always inherit object' && exit 3
grep -n $'\t\|\s$' $PYFILES && echo 'Error: tabs or trailing whitespace found, remove them' && exit 4
grep -Fn '.setlocale' ${PYFILES} && echo 'Error: do not use setlocale' && exit 5
grep -Fn '__future__ import with_statement' ${PYFILES} && echo 'Error: with_statement useless as we do not support Python 2.5' &&  exit 6
grep -nE '^[[:space:]]+except [[:alnum:] ]+,[[:alnum:] ]+' ${PYFILES} && echo 'Error: use new "as" way of naming exceptions' && exit 7
grep -nE "^ *print " ${PYFILES} && echo 'Error: Use the print function' && exit 8
grep -Fn ".has_key" ${PYFILES} && echo 'Error: Deprecated, use operator "in"' && exit 9
grep -Fn "os.isatty" ${PYFILES} && echo 'Error: Use stream.isatty() instead of os.isatty(stream.fileno())' && exit 10
grep -Fn "raise StopIteration" ${PYFILES} && echo 'Error: PEP 479' && exit 11
if [ "$VER" -eq 3 ]; then
    grep -nE "\.iter(keys|values|items)\(\)" ${PYFILES} | grep -Fv "six.iter" && echo 'Error: iterkeys/itervalues/iteritems is forbidden' && exit 12
fi

MODULE_FILES=$(git ls-files|grep '^modules/.*\.py$'|tr '\n' ' ')
grep -nE "^ *print(\(| )" ${MODULE_FILES} && echo 'Error: Use of print in modules is forbidden, use logger instead' && exit 20
if [ "$VER" -eq 3 ]; then
    grep -n xrange ${MODULE_FILES} && echo 'Error: xrange is forbidden' && exit 21
    grep -nE "from (urllib|urlparse) import" ${MODULE_FILES} && echo 'Error: python2 urllib is forbidden' && exit 22
    grep -nE "import (urllib|urlparse)$" ${MODULE_FILES} && echo 'Error: python2 urllib is forbidden' && exit 22
fi

FLAKE8=""
if which flake8 >/dev/null 2>&1; then
    FLAKE8=$(which flake8)
fi
if which flake8-python3 >/dev/null 2>&1; then
    FLAKE8=$(which flake8-python$VER)
fi

if [ -n "${FLAKE8}" ]; then
    exec env python$VER ${FLAKE8} --select=E9,F *.py $PYFILES
else
    PYFLAKES=""
    if [ "$VER" -eq 3 ] && which pyflakes3 >/dev/null 2>&1; then
        PYFLAKES=pyflakes3
    fi
    if which pyflakes >/dev/null 2>&1; then
        PYFLAKES=pyflakes
    fi
    if [ -z "${PYFLAKES}" ]
    then
        echo "pyflakes not found"
        exit 1
    fi
    # check for modern pyflakes
    if ${PYFLAKES} --version >/dev/null 2>&1; then
        exec ${PYFLAKES} $PYFILES
    else
        # hide error reported by mistake.
        # grep will return 0 only if it founds something, but our script
        # wants to return 0 when it founds nothing!
        ${PYFLAKES} $PYFILES | grep -v redefinition && exit 1 || exit 0
    fi
 fi
