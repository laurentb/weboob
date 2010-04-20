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

from __future__ import with_statement

import re
import os
import stat
from ConfigParser import SafeConfigParser
from logging import warning, debug

import weboob.backends
from weboob.backend import BaseBackend
from weboob.capabilities.cap import ICap


__all__ = ['Module']


class Module:
    def __init__(self, name, module):
        self.name = name
        self.module = module
        self.klass = None
        for attrname in dir(self.module):
            attr = getattr(self.module, attrname)
            if isinstance(attr, type) and issubclass(attr, BaseBackend) and attr != BaseBackend:
                self.klass = attr

        if not self.klass:
            raise ImportError("This is not a backend module (no BaseBackend class found)")

    def get_name(self):
        return self.klass.NAME

    def get_maintainer(self):
        return '%s <%s>' % (self.klass.MAINTAINER, self.klass.EMAIL)

    def get_version(self):
        return self.klass.VERSION

    def get_description(self):
        return self.klass.DESCRIPTION

    def get_license(self):
        return self.klass.LICENSE

    def get_config(self):
        return self.klass.CONFIG

    def iter_caps(self):
        for cap in self.klass.__bases__:
            if issubclass(cap, ICap) and cap != ICap:
                yield cap

    def has_caps(self, *caps):
        for c in caps:
            if issubclass(self.klass, c):
                return True
        return False

    def create_backend(self, weboob, name, config, storage):
        debug('Created backend "%s"' % name)
        return self.klass(weboob, name, config, storage)

class BackendsConfig(object):
    class WrongPermissions(Exception):
        pass

    def __init__(self, confpath):
        self.confpath = confpath
        try:
            mode = os.stat(confpath).st_mode
        except OSError:
            os.mknod(confpath, 0600)
        else:
            if mode & stat.S_IRGRP or mode & stat.S_IROTH:
                raise self.WrongPermissions(
                    u'Weboob will not start until config file %s is readable by group or other users.' % confpath)

    def iter_backends(self):
        config = SafeConfigParser()
        config.read(self.confpath)
        for name in config.sections():
            params = dict(config.items(name))
            try:
                yield name, params.pop('_type'), params
            except KeyError:
                warning('Missing field "_type" for backend "%s"', name)
                continue

    def add_backend(self, name, _type, params):
        config = SafeConfigParser()
        config.read(self.confpath)
        config.add_section(name)
        config.set(name, '_type', _type)
        for key, value in params.iteritems():
            config.set(name, key, value)
        with open(self.confpath, 'wb') as f:
            config.write(f)

    def remove_backend(self, name):
        config = SafeConfigParser()
        config.read(self.confpath)
        config.remove_section(name)
        with open(self.confpath, 'wb') as f:
            config.write(f)

class ModulesLoader(object):
    def __init__(self):
        self.modules = {}

    def get_or_load_module(self, name):
        if name not in self.modules:
            self.load_module('weboob.backends.%s' % name)
        return self.modules[name]

    def load(self):
        path = weboob.backends.__path__[0]
        regexp = re.compile('^%s/([\w\d_]+)$' % path)
        for root, dirs, files in os.walk(path):
            m = regexp.match(root)
            if m and '__init__.py' in files:
                self.load_module('weboob.backends.%s' % m.group(1))

    def load_module(self, name):
        try:
            module = Module(name, __import__(name, fromlist=[name]))
        except ImportError, e:
            warning('Unable to load module "%s": %s' % (name, e))
            return
        if name in self.modules:
            warning('Module "%s" is already loaded (%s)' % self.modules[name].module)
            return
        self.modules[module.get_name()] = module
        debug('Loaded module "%s" (%s)' % (name, module.module.__name__))
