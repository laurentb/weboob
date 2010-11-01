# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import logging
import os
import re

from weboob.capabilities.base import IBaseCap
from weboob.tools.backend import BaseBackend
from weboob.tools.log import getLogger


__all__ = ['Module', 'ModulesLoader']


class Module(object):
    def __init__(self, package):
        self.logger = getLogger('backend')
        self.package = package
        self.klass = None
        for attrname in dir(self.package):
            attr = getattr(self.package, attrname)
            if isinstance(attr, type) and issubclass(attr, BaseBackend) and attr != BaseBackend:
                self.klass = attr
        if not self.klass:
            raise ImportError('%s is not a backend (no BaseBackend class found)' % package)

    @property
    def name(self):
        return self.klass.NAME

    @property
    def maintainer(self):
        return '%s <%s>' % (self.klass.MAINTAINER, self.klass.EMAIL)

    @property
    def version(self):
        return self.klass.VERSION

    @property
    def description(self):
        return self.klass.DESCRIPTION

    @property
    def license(self):
        return self.klass.LICENSE

    @property
    def config(self):
        return self.klass.CONFIG

    @property
    def website(self):
        if self.klass.BROWSER and hasattr(self.klass.BROWSER, 'DOMAIN') and self.klass.BROWSER.DOMAIN:
            return '%s://%s' % (self.klass.BROWSER.PROTOCOL, self.klass.BROWSER.DOMAIN)
        else:
            return None

    @property
    def icon_path(self):
        return self.klass.ICON

    def iter_caps(self):
        for cap in self.klass.__bases__:
            if issubclass(cap, IBaseCap) and cap != IBaseCap:
                yield cap

    def has_caps(self, *caps):
        for c in caps:
            if (isinstance(c, basestring) and c in [cap.__name__ for cap in self.iter_caps()]) or \
               (type(c) == type and issubclass(self.klass, c)):
                return True
        return False

    def create_instance(self, weboob, instance_name, config, storage):
        backend_instance = self.klass(weboob, instance_name, config, storage, self.logger)
        self.logger.debug(u'Created backend instance "%s" for backend "%s"' % (instance_name, self.name))
        return backend_instance


class ModulesLoader(object):
    def __init__(self):
        self.loaded = {}
        self.logger = getLogger('modules')

    def get_or_load_module(self, module_name):
        if module_name not in self.loaded:
            self.load_module(module_name)
        if module_name in self.loaded:
            return self.loaded[module_name]
        else:
            return None

    def iter_existing_module_names(self):
        try:
            import weboob.backends
        except ImportError:
            return
        for path in weboob.backends.__path__:
            regexp = re.compile('^%s/([\w\d_]+)$' % path)
            for root, dirs, files in os.walk(path):
                m = regexp.match(root)
                if m and '__init__.py' in files:
                    yield m.group(1)

    def load_all(self):
        for existing_module_name in self.iter_existing_module_names():
            self.load_module(existing_module_name)

    def load_module(self, module_name):
        try:
            package_name = 'weboob.backends.%s' % module_name
            module = Module(__import__(package_name, fromlist=[str(package_name)]))
        except ImportError, e:
            msg = u'Unable to load module "%s": %s' % (module_name, e)
            if logging.root.level == logging.DEBUG:
                self.logger.exception(msg)
                return
            else:
                self.logger.error(msg)
                return
        if module.name in self.loaded:
            self.logger.debug('Module "%s" is already loaded from %s' % (module_name, module.package.__path__[0]))
            return
        self.loaded[module.name] = module
        self.logger.debug('Loaded module "%s" from %s' % (module_name, module.package.__path__[0]))
