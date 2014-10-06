#!/usr/bin/env python
from __future__ import print_function

# Hint: use this script with file:///path/to/local/modules/ in sources.list
# if you want to correctly check all modules.

from weboob.core import Weboob
import os

weboob = Weboob()
weboob.modules_loader.load_all()

backends_without_tests = []
backends_without_icons = []

for name, backend in weboob.modules_loader.loaded.iteritems():
    path = backend.package.__path__[0]
    if not os.path.exists(os.path.join(path, 'test.py')):
        backends_without_tests.append(name)
    if not os.path.exists(os.path.join(path, 'favicon.png')) and \
       not os.path.exists(os.path.join(weboob.repositories.icons_dir, '%s.png' % name)) and \
       not backend.icon:
        backends_without_icons.append(name)

if backends_without_tests:
    print('Modules without tests: %s' % backends_without_tests)
if backends_without_icons:
    print('Modules without icons: %s' % backends_without_icons)
