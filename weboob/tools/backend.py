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


import re
import os
from threading import RLock
from logging import debug

from weboob.capabilities.base import CapBaseObject, FieldNotFound, IBaseCap, NotLoaded
from weboob.tools.misc import iter_fields


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
    # Values must be ConfigField objects.
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

    class ConfigField(object):
        def __init__(self, default=None, is_masked=False, regexp=None, description=None, choices=None):
            self.default = default
            self.is_masked = is_masked
            self.regexp = regexp
            self.description = description
            self.choices = choices

    class ConfigError(Exception): pass

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, t, v, tb):
        self.lock.release()

    def __repr__(self):
        return u"<Backend '%s'>" % self.name

    def __init__(self, weboob, name, config, storage):
        self.weboob = weboob
        self.name = name
        self.lock = RLock()

        # Private fields (which start with '_')
        self._private_config = dict([(key, value) for key, value in config.iteritems() if key.startswith('_')])

        # Configuration of backend
        self.config = {}
        for name, field in self.CONFIG.iteritems():
            value = config.get(name, field.default)

            if value is None:
                raise BaseBackend.ConfigError('Missing parameter "%s" (%s)' % (name, field.description))

            if field.regexp and not re.match(field.regexp, str(value)):
                raise BaseBackend.ConfigError('Value of "%s" does not match regexp "%s"' % (name, field.regexp))

            if not field.default is None:
                if isinstance(field.default, bool) and not isinstance(value, bool):
                    value = value.lower() in ('1', 'true', 'on', 'yes')
                elif isinstance(field.default, int) and not isinstance(value, int):
                    value = int(value)
                elif isinstance(field.default, float) and not isinstance(value, float):
                    value = float(value)

            if field.choices:
                if (isinstance(field.choices, (tuple,list)) and not value in field.choices) or \
                   (isinstance(field.choices, dict) and not value in field.choices.iterkeys()):
                    raise BaseBackend.ConfigError('Value of "%s" might be in this list: %s' % (name,
                                                  ', '.join([s for s in (field.choices.iterkeys() if isinstance(field.choices, dict)
                                                                                                  else field.choices)])))
            self.config[name] = value
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
    def ICON(self):
        try:
            import xdg.IconTheme
        except ImportError:
            debug(u'Python xdg module was not found. Please install it to read icon files.')
        else:
            return xdg.IconTheme.getIconPath(self.NAME)

    @property
    def browser(self):
        """
        Attribute 'browser'. The browser is created at the first call
        of this attribute, to avoid useless pages access.

        Note that the 'create_default_browser' method is called to create it.
        """
        if not hasattr(self, '_browser'):
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
        elif 'HTTP_PROXY' in os.environ:
            kwargs['proxy'] = os.environ['HTTP_PROXY']

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
        @param fields  which fields to fill; if None, only "direct" fields are filled (list)
        """
        def not_loaded(v):
            return (v is NotLoaded or isinstance(v, CapBaseObject) and not v.__iscomplete__())

        if isinstance(fields, basestring):
            fields = (fields,)

        missing_fields = []
        if fields is None:
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
                debug(u'Fill %r with fields: %s' % (obj, missing_fields))
                return value(self, obj, missing_fields) or obj
