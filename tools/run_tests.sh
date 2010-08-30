#!/bin/bash

if [ "$1" != "" ]; then
	nosetests -sv $(dirname $0)/../weboob/backends/$1
else
	find $(dirname $0)/../weboob -name test.py | xargs nosetests -sv
fi
