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


from __future__ import with_statement

from ConfigParser import RawConfigParser
import logging
from logging import debug, error, exception, warning
import os
import re
import stat

from weboob.capabilities.base import IBaseCap
from weboob.tools.backend import BaseBackend


__all__ = ['Backend', 'BackendsConfig', 'BackendsLoader']


class Backend(object):
    def __init__(self, package):
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
    def icon_path(self):
        if self.klass.ICON is None:
            try:
                import xdg.IconTheme
            except ImportError:
                debug(u'Python xdg module was not found. Please install it to read icon files.')
            else:
                self.klass.ICON = xdg.IconTheme.getIconPath(self.klass.NAME)
        return self.klass.ICON

    def iter_caps(self):
        for cap in self.klass.__bases__:
            if issubclass(cap, IBaseCap) and cap != IBaseCap:
                yield cap

    def has_caps(self, *caps):
        for c in caps:
            if (isinstance(c, (unicode,str)) and c in [cap.__name__ for cap in self.iter_caps()]) or \
               (type(c) == type and issubclass(self.klass, c)):
                return True
        return False

    def create_instance(self, weboob, instance_name, config, storage):
        backend_instance = self.klass(weboob, instance_name, config, storage)
        debug(u'Created backend instance "%s" for backend "%s"' % (instance_name, self.name))
        return backend_instance


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
        config = RawConfigParser()
        config.read(self.confpath)
        for instance_name in config.sections():
            params = dict(config.items(instance_name))
            try:
                backend_name = params.pop('_backend')
            except KeyError:
                try:
                    backend_name = params.pop('_type')
                    logging.warning(u'Please replace _type with _backend in your config file "%s", for backend "%s"' % (
                        self.confpath, backend_name))
                except KeyError:
                    warning('Missing field "_backend" for configured backend "%s"', instance_name)
                    continue
            yield instance_name, backend_name, params

    def add_backend(self, instance_name, backend_name, params, edit=False):
        if not instance_name:
            raise ValueError(u'Please give a name to the configured backend.')
        config = RawConfigParser()
        config.read(self.confpath)
        if not edit:
            config.add_section(instance_name)
        config.set(instance_name, '_backend', backend_name)
        for key, value in params.iteritems():
            config.set(instance_name, key, value)
        with open(self.confpath, 'wb') as f:
            config.write(f)

    def edit_backend(self, instance_name, backend_name, params):
        return self.add_backend(instance_name, backend_name, params, True)

    def get_backend(self, instance_name):
        config = RawConfigParser()
        config.read(self.confpath)
        if not config.has_section(instance_name):
            raise KeyError(u'Configured backend "%s" not found' % instance_name)

        items = dict(config.items(instance_name))

        try:
            backend_name = items.pop('_backend')
        except KeyError:
            try:
                backend_name = items.pop('_type')
                logging.warning(u'Please replace _type with _backend in your config file "%s"' % self.confpath)
            except KeyError:
                warning('Missing field "_backend" for configured backend "%s"', instance_name)
                raise KeyError(u'Configured backend "%s" not found' % instance_name)
        return backend_name, items

    def remove_backend(self, instance_name):
        config = RawConfigParser()
        config.read(self.confpath)
        config.remove_section(instance_name)
        with open(self.confpath, 'w') as f:
            config.write(f)


class BackendsLoader(object):
    def __init__(self):
        self.loaded = {}

    def get_or_load_backend(self, backend_name):
        if backend_name not in self.loaded:
            self.load_backend(backend_name)
        if backend_name in self.loaded:
            return self.loaded[backend_name]
        else:
            return None

    def iter_existing_backend_names(self):
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
        for existing_backend_name in self.iter_existing_backend_names():
            self.load_backend(existing_backend_name)

    def load_backend(self, backend_name):
        try:
            package_name = 'weboob.backends.%s' % backend_name
            backend = Backend(__import__(package_name, fromlist=[str(package_name)]))
        except ImportError, e:
            msg = u'Unable to load backend "%s": %s' % (backend_name, e)
            if logging.root.level == logging.DEBUG:
                exception(msg)
                return
            else:
                error(msg)
                return
        if backend.name in self.loaded:
            debug('Backend "%s" is already loaded from %s' % (backend_name, backend.package.__path__[0]))
            return
        self.loaded[backend.name] = backend
        debug('Loaded backend "%s" from %s' % (backend_name, backend.package.__path__[0]))
