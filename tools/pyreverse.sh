#!/bin/sh
#
# Examples:
# pyreverse.sh weboob.backends.aum
#
# pyreverse is included in pylint Debian package

usage() {
    echo "pyreverse.sh <package_name>"
    exit
}

[ -z "$1" ] && usage

PYTHONPATH="$(dirname $0)/../modules/$1" pyreverse -p "$1" -o pdf -a1 -s1 "."
