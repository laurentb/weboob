#!/bin/bash
#
# Examples:
# pyreverse.sh weboob.backends.aum
#
# pyreverse is included in pylint Debian package

function usage() {
    echo "pyreverse.sh <package_name>"
    exit
}

[ -z "$1" ] && usage

pyreverse -p "$1" -a1 -s1 -o pdf "$1"
