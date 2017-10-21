#!/bin/bash -u
. "$(dirname $0)/common.sh"

err=0

PY3MODS=./tools/py3-compatible.modules

cd $(dirname $0)/..

MODULE_FILES=$(git ls-files|grep '^modules/.*\.py$')
MODULE_FILES3=$(printf "%s\n" $MODULE_FILES|grep -F -f $PY3MODS)

PYFILES=$(git ls-files | grep '^scripts\|\.py$'|grep -v boilerplate_data|grep -v '^modules'|grep -v '^contrib')
PYFILES3="$(printf "%s\n" $PYFILES | grep -v /deprecated/) $MODULE_FILES3"
PYFILES="$PYFILES $MODULE_FILES"
grep -n 'class [^( ]\+:$' ${PYFILES} && echo 'Error: old class style found, always inherit object' && err=3
grep -n $'\t\|\s$' ${PYFILES} && echo 'Error: tabs or trailing whitespace found, remove them' && err=4
grep -Fn '.setlocale' ${PYFILES} && echo 'Error: do not use setlocale' && err=5
grep -Fn '__future__ import with_statement' ${PYFILES} && echo 'Error: with_statement useless as we do not support Python 2.5' && err=6
grep -nE '^[[:space:]]+except [[:alnum:] ]+,[[:alnum:] ]+' ${PYFILES} && echo 'Error: use new "as" way of naming exceptions' && err=7
grep -nE "^ *print " ${PYFILES} && echo 'Error: Use the print function' && err=8
grep -Fn ".has_key" ${PYFILES} && echo 'Error: Deprecated, use operator "in"' && err=9
grep -Fn "os.isatty" ${PYFILES} && echo 'Error: Use stream.isatty() instead of os.isatty(stream.fileno())' && err=10
grep -Fn "raise StopIteration" ${PYFILES} && echo 'Error: PEP 479' && err=11

grep -nE "\.iter(keys|values|items)\(\)" ${PYFILES3} | grep -Fv "six.iter" && echo 'Error: iterkeys/itervalues/iteritems is forbidden' && err=12

grep -nE "^ *print(\(| )" ${MODULE_FILES} && echo 'Error: Use of print in modules is forbidden, use logger instead' && err=20
grep -n xrange ${MODULE_FILES3} && echo 'Error: xrange is forbidden' && err=21
grep -nE "from (urllib|urlparse) import" ${MODULE_FILES3} && echo 'Error: python2 urllib is forbidden' && err=22
grep -nE "^import (urllib|urlparse)$" ${MODULE_FILES3} && echo 'Error: python2 urllib is forbidden' && err=22

if [ ${VER} -eq 2 ]
then
  if ${PYTHON2} -c "import flake8" 2>/dev/null; then
      FLAKER2=flake8
      OPT2="--select=E9,F"
  elif ${PYTHON2} -c "import pyflakes" 2>/dev/null; then
      FLAKER2=pyflakes
      OPT2=
  else
      echo "flake8 or pyflakes for python2 not found"
      err=1
  fi
  if [ ${err} -ne 1 ]; then
    $PYTHON2 -m ${FLAKER2} ${OPT2} ${PYFILES} || err=32
  fi
fi

if [ ${VER} -eq 3 ]
then
  if ${PYTHON3} -c "import flake8" 2>/dev/null; then
      FLAKER3=flake8
      OPT3="--select=E9,F"
  elif ${PYTHON3} -c "import pyflakes" 2>/dev/null; then
      FLAKER3=pyflakes
      OPT3=
  else
      echo "flake8 or pyflakes for python3 not found"
      err=1
  fi
  if [ ${err} -ne 1 ]; then
    $PYTHON3 -m ${FLAKER3} ${OPT3} ${PYFILES3} || exit 33
  fi
fi

exit $err
