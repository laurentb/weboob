#!/bin/bash -u
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
MODULE_FILES=$(git ls-files|grep '^modules/.*\.py$'|tr '\n' ' ')
grep -nE "^ *print(\(| )" ${MODULE_FILES} && echo 'Error: Use of print in modules is forbidden, use logger instead' && exit 20

FLAKE8=""
if which flake8 >/dev/null 2>&1; then
    FLAKE8=flake8
fi
if which flake8-python2 >/dev/null 2>&1; then
    FLAKE8=flake8-python2
fi

if [ -n "${FLAKE8}" ]; then
    exec ${FLAKE8} --select=E9,F *.py $PYFILES
else
    PYFLAKES=""
    if which pyflakes >/dev/null 2>&1; then
        PYFLAKES=pyflakes
    fi
    if which pyflakes-python2 >/dev/null 2>&1; then
        PYFLAKES=pyflakes-python2
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
