#!/bin/sh
# This script greps imports excluding standard packages (the list is not exhaustive).
# It helps finding dependencies on a given directory.
# Execute it on a setuptools sdist directory.
#
# For example:
# ./tools/packaging/setup.py.d/core.py sdist
# => generates dist/weboob-core-x.y.tar.gz
# cd dist
# tar xzf weboob-core-x.y.tar.gz
# cd ..
# ./tools/packaging/find_imports.sh dist/weboob-core-x.y/weboob
#
# Then, add the results to the setup.py.d files,
# and to the tools/packaging/stdeb.cfg for Debian dependencies.

[ -z "$1" ] && echo "Please specify a directory" && exit

grep 'import' "$1" -r --include=*.py | \
egrep -w -v '^.+:.*weboob|__import__|__future__|logging|threading|ConfigParser|from \..*|copy|'\
'optparse|functools|inspect|datetime|ordereddict|from\ HTMLParser|xml\.etree|sqlite3|'\
're|time|os|sys|hashlib|subprocess|stat|__builtin__|tempfile|urllib|urllib2|types|traceback|'\
'getpass|htmlentitydefs|random|StringIO|minidom|from\ email|from\ smtplib|from\ smtpd|asyncore|'\
'wsgiref'

echo
echo "Used parsers:"
grep "tools\.parsers" "$1" -r --include=*.py
