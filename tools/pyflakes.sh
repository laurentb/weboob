#!/bin/bash -u
cd $(dirname $0)
cd ..

if which flake8 >/dev/null 2>&1; then
    set -e
    flake8 --ignore=E,W *.py weboob modules contrib scripts/*
else
    # grep will return 0 only if it founds something, but our script
    # wants to return 0 when it founds nothing!
    pyflakes *.py weboob modules contrib scripts/* | grep -v redefinition && exit 1 || exit 0
fi
