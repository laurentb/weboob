#!/bin/bash
set -e

case $1 in
-h|--help)
	echo "$0 [test] <backend name>"
	;;
test|tests)
	TEST_ONLY=1
	NAME=$2
	DOWNLOAD_ID=$3
	;;
*)
	NAME=$1
	;;
esac

USERNAME="$(git config --get user.name)"
Backend=$(echo $NAME|(head -c 1|tr a-z A-Z; cat))
backend=$(echo $NAME|(head -c 1|tr A-Z a-z; cat))
BACKEND_CLASS=$Backend"Backend"
BACKEND_DIR=$(dirname $0)/../weboob/backends/$backend

HEADER="\
# -*- coding: utf-8 -*-

# Copyright(C) $(date +%Y) $USERNAME
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.
"

if [ -z $TEST_ONLY ]
then
	mkdir $BACKEND_DIR
	
	echo >$BACKEND_DIR/__init__.py "$HEADER

from .backend import $BACKEND_CLASS

__all__ = ['$BACKEND_CLASS']
"

	echo >$BACKEND_DIR/backend.py "$HEADER

from weboob.tools.capabilities.gallery.genericcomicreader import GenericComicReaderBackend, DisplayPage

__all__ = ['$BACKEND_CLASS']

class $BACKEND_CLASS(GenericComicReaderBackend):
    NAME = '$backend'
    DESCRIPTION = '$Backend manga reading site'
    DOMAIN = 'www.$backend.com'
    BROWSER_PARAMS = dict(
        img_src_xpath=\"//img[@id='comic_page']/@src\",
        page_list_xpath=\"(//select[@id='page_select'])[1]/option/@value\")
    ID_REGEXP = r'[^/]+/[^/]+'
    URL_REGEXP = r'.+$backend.com/(%s).+' % ID_REGEXP
    ID_TO_URL = 'http://www.$backend.com/%s'
    PAGES = { URL_REGEXP: DisplayPage }
"
fi

echo >$BACKEND_DIR/test.py "$HEADER
from weboob.tools.capabilities.gallery.genericcomicreader import GenericComicReaderTest

class $Backend""Test(GenericComicReaderTest):
    BACKEND = '$backend'
    DOWNLOAD_ID = '$DOWNLOAD_ID'
"

echo Now please edit files in $BACKEND_DIR
