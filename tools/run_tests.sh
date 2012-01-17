#!/bin/bash

if [ "$1" != "" ]; then
	nosetests -sv $(dirname $0)/../modules/$1
else
	find $(dirname $0)/../weboob $(dirname $0)/../modules -name test.py | xargs nosetests -sv
fi
