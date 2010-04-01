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

import re
import os
from ConfigParser import SafeConfigParser
from logging import warning, debug
from types import ClassType

import weboob.backends as backends
from weboob.backend import Backend

class Module:
    def __init__(self, name, module):
        self.name = name
        self.module = module
        self.klass = None
        for attrname in dir(self.module):
            attr = getattr(self.module, attrname)
            if isinstance(attr, ClassType) and issubclass(attr, Backend) and attr != Backend:
                self.klass = attr

        if not self.klass:
            raise ImportError("This is not a backend module (no Backend class found)")

    def get_name(self):
        return self.klass.NAME

    def has_caps(self, *caps):
        for c in caps:
            if issubclass(self.klass, c):
                return True
        return False

    def create_backend(self, weboob, config):
        return self.klass(weboob, config)

class ModulesLoader:
    def __init__(self):
        self.modules = {}

    def load(self):
        path = backends.__path__[0]
        regexp = re.compile('^%s/([\w\d_]+)$' % path)
        for root, dirs, files in os.walk(path):
            m = regexp.match(root)
            if m and '__init__.py' in files:
                self.load_module('weboob.backends.%s' % m.group(1))

    def load_module(self, name):
        try:
            module = Module(name, __import__(name, fromlist=[name]))
        except ImportError, e:
            warning('Unable to load module %s: %s' % (name, e))
            return
        if name in self.modules:
            warning('Module "%s" is already loaded (%s)' % self.modules[name].module)
            return
        self.modules[module.get_name()] = module
        debug('Loaded module %s (%s)' % (name, module.module.__name__))

    def load_backends(self, confpath, caps, names):
        config = SafeConfigParser()
        config.read(confpath)
        backends = {}
        for name in config.sections():
            params = dict(config.items(name))
            try:
                module = self.modules[params['_type']]
            except KeyError:
                warning('Unable to find module %s', name)
                continue

            # Check conditions
            if (not caps is None and not module.has_caps(caps)) or \
               (not names is None and not module.name in name):
                continue

            try:
                backends[name] = module.create_backend(self, params)
            except Exception, e:
                warning('Unable to load %s backend: %s' % (name, e))

        return backends

    def load_modules_as_backends(self, caps, names):
        backends = {}
        for name, module in self.modules.iteritems():
            if (caps is None or module.has_caps(caps)) and \
               (names is None or module.name in names):
                try:
                    backends[module.name] = module.create_backend(self, {})
                except Exception, e:
                    warning('Unable to load %s backend: %s' % (name, e))
        return backends
