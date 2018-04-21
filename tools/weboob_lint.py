#!/usr/bin/env python3
from __future__ import print_function

import logging
import os
import subprocess
import sys

from weboob.core import Weboob

# Hint: use this script with file:///path/to/local/modules/ in sources.list
# if you want to correctly check all modules.


logging.basicConfig()

weboob = Weboob()
weboob.modules_loader.load_all()

modules_without_tests = []
modules_without_icons = []
modules_using_deprecated = []

for name, module in weboob.modules_loader.loaded.items():
    path = module.package.__path__[0]
    if not os.path.exists(os.path.join(path, 'test.py')):
        modules_without_tests.append(name)
    if not os.path.exists(os.path.join(path, 'favicon.png')) and \
       not os.path.exists(os.path.join(weboob.repositories.icons_dir, '%s.png' % name)) and \
       not module.icon:
        modules_without_icons.append(name)

    if subprocess.call(['grep', '-q', '-r', 'weboob.deprecated.browser', path]) == 0:
        modules_using_deprecated.append(name)


if modules_without_tests:
    print('\nModules without tests: %s' % ', '.join(sorted(modules_without_tests)))
if modules_without_icons:
    print('\nModules without icons: %s' % ', '.join(sorted(modules_without_icons)))
if modules_using_deprecated:
    print('\nModules using deprecated Browser 1: %s' % ', '.join(sorted(modules_using_deprecated)))


if modules_without_tests or modules_without_icons or modules_using_deprecated:
    sys.exit(1)
