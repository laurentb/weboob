#!/usr/bin/env python3
from __future__ import print_function

# Hint: use this script with file:///path/to/local/modules/ in sources.list
# if you want to correctly check all modules.

from weboob.core import Weboob
import os
import sys
import subprocess

weboob = Weboob()
weboob.modules_loader.load_all()

backends_without_tests = []
backends_without_icons = []
backends_using_deprecated = []

for name, backend in weboob.modules_loader.loaded.items():
    path = backend.package.__path__[0]
    if not os.path.exists(os.path.join(path, 'test.py')):
        backends_without_tests.append(name)
    if not os.path.exists(os.path.join(path, 'favicon.png')) and \
       not os.path.exists(os.path.join(weboob.repositories.icons_dir, '%s.png' % name)) and \
       not backend.icon:
        backends_without_icons.append(name)

    if subprocess.call(['grep', '-q', '-r', 'weboob.deprecated.browser', path]) == 0:
        backends_using_deprecated.append(name)


if backends_without_tests:
    backends_without_tests.sort()
    print('Modules without tests: %s' % backends_without_tests)
if backends_without_icons:
    backends_without_icons.sort()
    print('Modules without icons: %s' % backends_without_icons)
if backends_using_deprecated:
    backends_using_deprecated.sort()
    print('Modules using deprecated Browser 1: %s' % backends_using_deprecated)


if backends_without_tests or backends_without_icons:
    sys.exit(1)
