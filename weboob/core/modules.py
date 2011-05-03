# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


import logging
import os

from weboob.capabilities.base import IBaseCap
from weboob.tools.backend import BaseBackend
from weboob.tools.log import getLogger


__all__ = ['Module', 'ModulesLoader', 'ModuleLoadError']


class ModuleLoadError(Exception):
    def __init__(self, module_name, msg):
        Exception.__init__(self, u'Unable to load module "%s": %s' % (module_name, msg))
        self.module = module_name

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
        return self.klass.iter_caps()

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
        """
        Can raise a ModuleLoadError exception.
        """
        if module_name not in self.loaded:
            self.load_module(module_name)
        return self.loaded[module_name]

    def iter_existing_module_names(self):
        try:
            import weboob.backends
        except ImportError:
            return
        for path in weboob.backends.__path__:
            for root, dirs, files in os.walk(path):
                if os.path.dirname( root ) == path and '__init__.py' in files:
                    s = os.path.basename( root )
                    yield s

    def load_all(self):
        for existing_module_name in self.iter_existing_module_names():
            try:
                self.load_module(existing_module_name)
            except ModuleLoadError, e:
                self.logger.warning(e)

    def load_module(self, module_name):
        try:
            package_name = 'weboob.backends.%s' % module_name
            module = Module(__import__(package_name, fromlist=[str(package_name)]))
        except Exception, e:
            if self.logger.level == logging.DEBUG:
                self.logger.exception(e)
            raise ModuleLoadError(module_name, e)
        if module.name in self.loaded:
            self.logger.debug('Module "%s" is already loaded from %s' % (module_name, module.package.__path__[0]))
            return
        self.loaded[module.name] = module
        self.logger.debug('Loaded module "%s" from %s' % (module_name, module.package.__path__[0]))
