#!/bin/bash -u
cd $(dirname $0)
cd ..
PYFILES=$(git ls-files|grep '^scripts\|\.py$'|grep -v boilerplate_data|tr '\n' ' ')
grep 'class [^( ]\+:$' ${PYFILES} && exit 3
grep $'\t\|\s$' $PYFILES && exit 4
grep '\.setlocale' ${PYFILES} && exit 5

FLAKE8=""
if which flake8 >/dev/null 2>&1; then
    FLAKE8=flake8
fi
if which flake8-python2 >/dev/null 2>&1; then
    FLAKE8=flake8-python2
fi

if [ -n "${FLAKE8}" ]; then
    set -e
    ${FLAKE8} --ignore=E,W --exclude='*_ui.py' *.py $PYFILES
else
    # grep will return 0 only if it founds something, but our script
    # wants to return 0 when it founds nothing!
    pyflakes $PYFILES | grep -v redefinition && exit 1 || exit 0
fi
