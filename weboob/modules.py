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
import sys
from logging import warning

import weboob.backends as backends

class Backend:
    def __init__(self, name, module):
        self.name = name
        self.module = module

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
            backend = Backend(name, __import__(name, fromlist=[name]))
        except ImportError:
            warning('Unable to import %s (%s)' % (name, path))
            raise
            return
        if name in self.modules:
            warning('Module "%s" is already loaded (%s)' % self.modules[name].module)
            return
        self.modules[name] = backend
        print 'Loaded module %s (%s)' % (name, backend.module.__name__)
