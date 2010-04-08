# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

import os
from logging import warning

from weboob.modules import ModulesLoader, BackendsConfig
from weboob.scheduler import Scheduler

class Weboob:
    WORKDIR = os.path.join(os.path.expanduser('~'), '.weboob')
    BACKENDS_FILENAME = 'backends'

    def __init__(self, app_name, workdir=WORKDIR, backends_filename=None, scheduler=None):
        self.app_name = app_name
        self.workdir = workdir
        self.backends = {}

        # Scheduler
        if scheduler is None:
            scheduler = Scheduler()
        self.scheduler = scheduler

        # Create WORKDIR
        if not os.path.exists(self.workdir):
            os.mkdir(self.workdir)
        elif not os.path.isdir(self.workdir):
            warning('"%s" is not a directory' % self.workdir)

        # Modules loader
        self.modules_loader = ModulesLoader()

        # Backends config
        if not backends_filename:
            backends_filename = os.path.join(self.workdir, self.BACKENDS_FILENAME)
        elif not backends_filename.startswith('/'):
            backends_filename = os.path.join(self.workdir, backends_filename)
        self.backends_config = BackendsConfig(backends_filename)

    def load_backends(self, caps=None, names=None):
        for name, _type, params in self.backends_config.iter_backends():
            try:
                module = self.modules_loader.get_or_load_module(_type)
            except KeyError:
                warning('Unable to find module "%s" for backend "%s"' % (_type, name))
                continue

            # Check conditions
            if (not caps is None and not module.has_caps(caps)) or \
               (not names is None and not module.name in name):
                continue

            try:
                self.backends[name] = module.create_backend(self, name, params)
            except Exception, e:
                warning('Unable to load "%s" backend: %s. filename=%s' % (name, e, self.backends_config.confpath))

        return self.backends

    def load_modules(self, caps=None, names=None):
        self.modules_loader.load()
        for name, module in self.modules_loader.modules.iteritems():
            if (caps is None or module.has_caps(caps)) and \
               (names is None or module.name in names):
                try:
                    self.backends[module.name] = module.create_backend(self, module.name, {})
                except Exception, e:
                    warning('Unable to load "%s" module as backend with no config: %s' % (name, e))
        return self.backends

    def iter_backends(self, caps=None):
        for name, backend in self.backends.iteritems():
            if caps is None or backend.has_caps(caps):
                yield (name, backend)

    def schedule(self, interval, function, *args):
        return self.scheduler.schedule(interval, function, *args)

    def repeat(self, interval, function, *args):
        return self.scheduler.repeat(interval, function, *args)

    def loop(self):
        return self.scheduler.run()
