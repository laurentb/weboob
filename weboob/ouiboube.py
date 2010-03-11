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
import sched
import time

from weboob.modules import ModulesLoader
from weboob.config import Config

class Weboob:
    CONFIG_FILE = '%s/.weboob/config' % os.path.expanduser("~")
    DATA_DIR = '%s/.weboob/' % os.path.expanduser("~")

    def __init__(self, app_name, config_file=CONFIG_FILE, data_dir=DATA_DIR):
        self.app_name = app_name
        self.backends = {}
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.config = Config(self.CONFIG_FILE)
        self.config.load()
        self.modules_loader = ModulesLoader()
        self.modules_loader.load()

    def get_frontend_config(self, default={}):
        return self.config.get('frontends', self.app_name, default=default)

    def get_backend_config(self, backend_name, default={}):
        return self.config.get('backends', backend_name, default=default)

    def load_modules(self, caps=None, name=None):
        for name, module in self.modules_loader.modules.iteritems():
            if (not caps or module.has_caps(caps)) and \
               (not name or module.name == name):
                backend = module.create_backend(self)
                self.backends[module.name] = backend

    def load_module(self, modname, instname):
        module = self.modules_loader[modname]
        self.backends[instname] = module.create_backend(self)

    def iter_backends(self, caps=None):
        if caps is None:
            return self.backends.iteritems()
        else:
            return dict((name, backend) for name, backend in self.backends.iteritems()
                        if backend.has_caps(caps)).iteritems()

    def schedule(self, interval, function, *args):
        self.scheduler.enter(interval, 1, function, args)

    def loop(self):
        self.scheduler.run()
