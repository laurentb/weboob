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


import os
from threading import RLock

from weboob.capabilities.base import CapBaseObject, FieldNotFound, IBaseCap, NotLoaded
from weboob.tools.misc import iter_fields
from weboob.tools.log import getLogger


__all__ = ['BaseBackend', 'ObjectNotAvailable']


class ObjectNotAvailable(Exception):
    pass


class BackendStorage(object):
    def __init__(self, name, storage):
        self.name = name
        self.storage = storage

    def set(self, *args):
        if self.storage:
            return self.storage.set('backends', self.name, *args)

    def delete(self, *args):
        if self.storage:
            return self.storage.delete('backends', self.name, *args)

    def get(self, *args, **kwargs):
        if self.storage:
            return self.storage.get('backends', self.name, *args, **kwargs)
        else:
            return kwargs.get('default', None)

    def load(self, default):
        if self.storage:
            return self.storage.load('backends', self.name, default)

    def save(self):
        if self.storage:
            return self.storage.save('backends', self.name)


class BaseBackend(object):
    # Backend name.
    NAME = None
    # Name of the maintainer of this backend.
    MAINTAINER = '<unspecified>'
    # Email address of the maintainer.
    EMAIL = '<unspecified>'
    # Version of backend (for information only).
    VERSION = '<unspecified>'
    # Description
    DESCRIPTION = '<unspecified>'
    # License of this backend.
    LICENSE = '<unspecified>'
    # Icon file path
    ICON = None
    # Configuration required for this backend.
    # Values must be weboob.tools.value.Value objects.
    CONFIG = {}
    # Storage
    STORAGE = {}
    # Browser class
    BROWSER = None
    # Supported objects to fill
    # The key is the class and the value the method to call to fill
    # Method prototype: method(object, fields)
    # When the method is called, fields are only the one which are
    # NOT yet filled.
    OBJECTS = {}

    class ConfigError(Exception): pass

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, t, v, tb):
        self.lock.release()

    def __repr__(self):
        return u"<Backend '%s'>" % self.name

    def __init__(self, weboob, name, config, storage, logger=None):
        self.logger = getLogger(name, parent=logger)
        self.weboob = weboob
        self.name = name
        self.lock = RLock()

        # Private fields (which start with '_')
        self._private_config = dict((key, value) for key, value in config.iteritems() if key.startswith('_'))

        # Configuration of backend
        self.config = {}
        for name, field in self.CONFIG.iteritems():
            value = config.get(name, None)

            if value is None:
                if field.required:
                    raise BaseBackend.ConfigError('Backend(%s): Configuration error: Missing parameter "%s" (%s)' % (self.name, name, field.description))
                value = field.default

            try:
                field.set_value(value)
            except ValueError, v:
                raise BaseBackend.ConfigError('Backend(%s): Configuration error for field "%s": %s' % (self.name, name, v))

            # field.value is a property which converts string to right type (bool/int/float)
            self.config[name] = field.value
        self.storage = BackendStorage(self.name, storage)
        self.storage.load(self.STORAGE)

    def deinit(self):
        """
        This abstract method is called when the backend is unloaded.
        """
        pass

    class classprop(object):
        def __init__(self, fget):
            self.fget = fget
        def __get__(self, inst, objtype=None):
            if inst:
                return self.fget(inst)
            else:
                return self.fget(objtype)

    @classprop
    def ICON(klass):
        try:
            import xdg.IconTheme
        except ImportError:
            getLogger(klass.NAME).debug(u'Python xdg module was not found. Please install it to read icon files.')
        else:
            return xdg.IconTheme.getIconPath(klass.NAME)

    _browser = None

    @property
    def browser(self):
        """
        Attribute 'browser'. The browser is created at the first call
        of this attribute, to avoid useless pages access.

        Note that the 'create_default_browser' method is called to create it.
        """
        if self._browser is None:
            self._browser = self.create_default_browser()
        return self._browser

    def create_default_browser(self):
        """
        Method to overload to build the default browser in
        attribute 'browser'.
        """
        return self.create_browser()

    def create_browser(self, *args, **kwargs):
        """
        Build a browser from the BROWSER class attribute and the
        given arguments.
        """
        if not self.BROWSER:
            return None

        if '_proxy' in self._private_config:
            kwargs['proxy'] = self._private_config['_proxy']
        elif 'http_proxy' in os.environ:
            kwargs['proxy'] = os.environ['http_proxy']
        elif 'HTTP_PROXY' in os.environ:
            kwargs['proxy'] = os.environ['HTTP_PROXY']
        kwargs['logger'] = self.logger

        return self.BROWSER(*args, **kwargs)

    def iter_caps(self):
        for cap in self.__class__.__bases__:
            if issubclass(cap, IBaseCap) and cap != IBaseCap:
                yield cap

    def has_caps(self, *caps):
        for c in caps:
            if (isinstance(c, basestring) and c in [cap.__name__ for cap in self.iter_caps()]) or \
               isinstance(self, c):
                return True
        return False

    def fillobj(self, obj, fields=None):
        """
        @param fields  which fields to fill; if None, all fields are filled (list)
        """
        def not_loaded(v):
            return (v is NotLoaded or isinstance(v, CapBaseObject) and not v.__iscomplete__())

        if isinstance(fields, basestring):
            fields = (fields,)

        missing_fields = []
        if fields is None:
            # Select all fields
            if isinstance(obj, CapBaseObject):
                fields = [item[0] for item in obj.iter_fields()]
            else:
                fields = [item[0] for item in iter_fields(obj)]

        for field in fields:
            if not hasattr(obj, field):
                raise FieldNotFound(obj, field)
            value = getattr(obj, field)

            missing = False
            if hasattr(value, '__iter__'):
                for v in (value.itervalues() if isinstance(value, dict) else value):
                    if not_loaded(v):
                        missing = True
                        break
            elif not_loaded(value):
                missing = True

            if missing:
                missing_fields.append(field)

        if not missing_fields:
            return obj

        assert type(obj) in self.OBJECTS, 'The object of type %s is not supported by the backend %s' % (type(obj), self)

        for key, value in self.OBJECTS.iteritems():
            if isinstance(obj, key):
                self.logger.debug(u'Fill %r with fields: %s' % (obj, missing_fields))
                return value(self, obj, missing_fields) or obj
