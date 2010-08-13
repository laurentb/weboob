#!/bin/bash

find $(dirname $0)/../weboob -name test.py | xargs nosetests -sv
