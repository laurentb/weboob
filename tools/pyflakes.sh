#!/bin/bash
if [ `basename $PWD` == 'tools' ]; then
        cd ..
fi
pyflakes weboob scripts/* | grep -v __init__.py
