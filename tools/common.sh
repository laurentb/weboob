VER=3
if [ "${1-}" = "-2" ]; then
    VER=2
    shift
fi


if [ -z "${PYTHON2-}" ]; then
    which python2.7 >/dev/null 2>&1 && PYTHON2=$(which python2.7)
    which python2 >/dev/null 2>&1 && PYTHON2=$(which python2)
fi

if [ -z "${PYTHON3-}" ]; then
    which python3.5 >/dev/null 2>&1 && PYTHON3=$(which python3.5)
    which python3.6 >/dev/null 2>&1 && PYTHON3=$(which python3.6)
    which python3.7 >/dev/null 2>&1 && PYTHON3=$(which python3.7)
    which python3.8 >/dev/null 2>&1 && PYTHON3=$(which python3.8)
    which python3 >/dev/null 2>&1 && PYTHON3=$(which python3)
fi

if [ -z "${PYTHON-}" ]; then
    which python >/dev/null 2>&1 && PYTHON=$(which python)
    if [ $VER -eq 2 -a -n "${PYTHON2}" ]; then
        PYTHON=${PYTHON2}
    elif [ $VER -eq 3 -a -n "${PYTHON3}" ]; then
        PYTHON=${PYTHON3}
    fi
fi
