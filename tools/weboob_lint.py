#!/usr/bin/env python

from weboob.core.modules import ModulesLoader

loader = ModulesLoader()
loader.load_all()

backends_without_icons = [name for name, backend in loader.loaded.iteritems() if backend.icon_path is None]
if backends_without_icons:
    print 'Backends without icons: %s' % backends_without_icons
