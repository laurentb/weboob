#!/usr/bin/env python

from weboob.core.modules import ModulesLoader
import weboob.backends
import os

loader = ModulesLoader()
loader.load_all()

backends_without_icons = [name for name, backend in loader.loaded.iteritems() if backend.icon_path is None]
if backends_without_icons:
    print 'Backends without icons: %s' % backends_without_icons

backends_without_tests = []
for name, backend in loader.loaded.iteritems():
    if not os.path.exists(os.path.join(weboob.backends.__path__[0], name, 'test.py')):
        backends_without_tests.append(name)
if backends_without_tests:
    print 'Backends without tests: %s' % backends_without_tests
