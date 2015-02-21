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
from copy import copy

from weboob.capabilities.base import BaseObject, FieldNotFound, \
    Capability, NotLoaded, NotAvailable
from weboob.tools.misc import iter_fields
from weboob.tools.log import getLogger
from weboob.tools.value import ValuesDict


__all__ = ['BackendStorage', 'BackendConfig', 'Module']


class BackendStorage(object):
    """
    This is an abstract layer to store data in storages (:mod:`weboob.tools.storage`)
    easily.

    It is instancied automatically in constructor of :class:`Module`, in the
    :attr:`Module.storage` attribute.

    :param name: name of backend
    :param storage: storage object
    :type storage: :class:`weboob.tools.storage.IStorage`
    """

    def __init__(self, name, storage):
        self.name = name
        self.storage = storage

    def set(self, *args):
        """
        Set value in the storage.

        Example:

        >>> from weboob.tools.storage import StandardStorage
        >>> backend = BackendStorage('blah', StandardStorage('/tmp/cfg'))
        >>> backend.storage.set('config', 'nb_of_threads', 10)
        >>>

        :param args: the path where to store value
        """
        if self.storage:
            return self.storage.set('backends', self.name, *args)

    def delete(self, *args):
        """
        Delete a value from the storage.

        :param args: path to delete.
        """
        if self.storage:
            return self.storage.delete('backends', self.name, *args)

    def get(self, *args, **kwargs):
        """
        Get a value or a dict of values in storage.

        Example:

        >>> from weboob.tools.storage import StandardStorage
        >>> backend = BackendStorage('blah', StandardStorage('/tmp/cfg'))
        >>> backend.storage.get('config', 'nb_of_threads')
        10
        >>> backend.storage.get('config', 'unexistant', 'path', default='lol')
        'lol'
        >>> backend.storage.get('config')
        {'nb_of_threads': 10, 'other_things': 'blah'}

        :param args: path to get
        :param default: if specified, default value when path is not found
        """
        if self.storage:
            return self.storage.get('backends', self.name, *args, **kwargs)
        else:
            return kwargs.get('default', None)

    def load(self, default):
        """
        Load storage.

        It is made automatically when your backend is created, and use the
        ``STORAGE`` class attribute as default.

        :param default: this is the default tree if storage is empty
        :type default: :class:`dict`
        """
        if self.storage:
            return self.storage.load('backends', self.name, default)

    def save(self):
        """
        Save storage.
        """
        if self.storage:
            return self.storage.save('backends', self.name)


class BackendConfig(ValuesDict):
    """
    Configuration of a backend.

    This class is firstly instanced as a :class:`weboob.tools.value.ValuesDict`,
    containing some :class:`weboob.tools.value.Value` (and derivated) objects.

    Then, using the :func:`load` method will load configuration from file and
    create a copy of the :class:`BackendConfig` object with the loaded values.
    """
    modname = None
    instname = None
    weboob = None

    def load(self, weboob, modname, instname, config, nofail=False):
        """
        Load configuration from dict to create an instance.

        :param weboob: weboob object
        :type weboob: :class:`weboob.core.ouiboube.Weboob`
        :param modname: name of the module
        :type modname: :class:`str`
        :param instname: name of this backend
        :type instname: :class:`str`
        :param params: parameters to load
        :type params: :class:`dict`
        :param nofail: if true, this call can't fail
        :type nofail: :class:`bool`
        :rtype: :class:`BackendConfig`
        """
        cfg = BackendConfig()
        cfg.modname = modname
        cfg.instname = instname
        cfg.weboob = weboob
        for name, field in self.iteritems():
            value = config.get(name, None)

            if value is None:
                if not nofail and field.required:
                    raise Module.ConfigError('Backend(%s): Configuration error: Missing parameter "%s" (%s)'
                                                  % (cfg.instname, name, field.description))
                value = field.default

            field = copy(field)
            try:
                field.load(cfg.instname, value, cfg.weboob.callbacks)
            except ValueError as v:
                if not nofail:
                    raise Module.ConfigError(
                        'Backend(%s): Configuration error for field "%s": %s' % (cfg.instname, name, v))

            cfg[name] = field
        return cfg

    def dump(self):
        """
        Dump config in a dictionary.

        :rtype: :class:`dict`
        """
        settings = {}
        for name, value in self.iteritems():
            settings[name] = value.dump()
        return settings

    def save(self, edit=True, params=None):
        """
        Save backend config.

        :param edit: if true, it changes config of an existing backend
        :type edit: :class:`bool`
        :param params: if specified, params to merge with the ones of the current object
        :type params: :class:`dict`
        """
        assert self.modname is not None
        assert self.instname is not None
        assert self.weboob is not None

        dump = self.dump()
        if params is not None:
            dump.update(params)

        self.weboob.backends_config.add_backend(self.instname, self.modname, dump, edit)


class Module(object):
    """
    Base class for modules.

    You may derivate it, and also all capabilities you want to implement.

    :param weboob: weboob instance
    :type weboob: :class:`weboob.core.ouiboube.Weboob`
    :param name: name of backend
    :type name: :class:`str`
    :param config: configuration of backend
    :type config: :class:`dict`
    :param storage: storage object
    :type storage: :class:`weboob.tools.storage.IStorage`
    :param logger: logger
    :type logger: :class:`logging.Logger`
    """
    # Module name.
    NAME = None
    # Name of the maintainer of this module.
    MAINTAINER = u'<unspecified>'
    # Email address of the maintainer.
    EMAIL = '<unspecified>'
    # Version of module (for information only).
    VERSION = '<unspecified>'
    # Description
    DESCRIPTION = '<unspecified>'
    # License of this module.
    LICENSE = '<unspecified>'
    # Configuration required for backends.
    # Values must be weboob.tools.value.Value objects.
    CONFIG = BackendConfig()
    # Storage
    STORAGE = {}
    # Browser class
    BROWSER = None
    # URL to an optional icon.
    # If you want to create your own icon, create a 'favicon.ico' ico in
    # the module's directory, and keep the ICON value to None.
    ICON = None
    # Supported objects to fill
    # The key is the class and the value the method to call to fill
    # Method prototype: method(object, fields)
    # When the method is called, fields are only the one which are
    # NOT yet filled.
    OBJECTS = {}

    class ConfigError(Exception):
        """
        Raised when the config can't be loaded.
        """

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, t, v, tb):
        self.lock.release()

    def __repr__(self):
        return u"<Backend %r>" % self.name

    def __init__(self, weboob, name, config=None, storage=None, logger=None):
        self.logger = getLogger(name, parent=logger)
        self.weboob = weboob
        self.name = name
        self.lock = RLock()
        if config is None:
            config = {}

        # Private fields (which start with '_')
        self._private_config = dict((key, value) for key, value in config.iteritems() if key.startswith('_'))

        # Load configuration of backend.
        self.config = self.CONFIG.load(weboob, self.NAME, self.name, config)

        self.storage = BackendStorage(self.name, storage)
        self.storage.load(self.STORAGE)

    def deinit(self):
        """
        This abstract method is called when the backend is unloaded.
        """
        if self._browser is None:
            return

        if hasattr(self.browser, 'dump_state'):
            self.storage.set('browser_state', self.browser.dump_state())
            self.storage.save()

    _browser = None

    @property
    def browser(self):
        """
        Attribute 'browser'. The browser is created at the first call
        of this attribute, to avoid useless pages access.

        Note that the :func:`create_default_browser` method is called to create it.
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

        tmpproxy = None
        tmpproxys = None

        if '_proxy' in self._private_config:
            tmpproxy = self._private_config['_proxy']
        elif 'http_proxy' in os.environ:
            tmpproxy = os.environ['http_proxy']
        elif 'HTTP_PROXY' in os.environ:
            tmpproxy = os.environ['HTTP_PROXY']
        if '_proxy_ssl' in self._private_config:
            tmpproxys = self._private_config['_proxy_ssl']
        elif 'https_proxy' in os.environ:
            tmpproxys = os.environ['https_proxy']
        elif 'HTTPS_PROXY' in os.environ:
            tmpproxys = os.environ['HTTPS_PROXY']

        if any((tmpproxy, tmpproxys)):
            kwargs['proxy'] = {}
            if tmpproxy is not None:
                kwargs['proxy']['http'] = tmpproxy
            if tmpproxys is not None:
                kwargs['proxy']['https'] = tmpproxys


        kwargs['logger'] = self.logger

        if self.logger.settings['responses_dirname']:
            kwargs.setdefault('responses_dirname', os.path.join(self.logger.settings['responses_dirname'],
                                                                self._private_config.get('_debug_dir', self.name)))

        browser = self.BROWSER(*args, **kwargs)

        if hasattr(browser, 'load_state'):
            browser.load_state(self.storage.get('browser_state', default={}))

        return browser

    @classmethod
    def iter_caps(klass):
        """
        Iter capabilities implemented by this backend.

        :rtype: iter[:class:`weboob.capabilities.base.Capability`]
        """
        def iter_caps(cls):
            for base in cls.__bases__:
                if issubclass(base, Capability) and base != Capability:
                    yield base
                    for cap in iter_caps(base):
                        yield cap
        return iter_caps(klass)

    def has_caps(self, *caps):
        """
        Check if this backend implements at least one of these capabilities.
        """
        for c in caps:
            if (isinstance(c, basestring) and c in [cap.__name__ for cap in self.iter_caps()]) or \
               isinstance(self, c):
                return True
        return False

    def fillobj(self, obj, fields=None):
        """
        Fill an object with the wanted fields.

        :param fields: what fields to fill; if None, all fields are filled
        :type fields: :class:`list`
        """
        if obj is None:
            return obj

        def not_loaded(v):
            return (v is NotLoaded or isinstance(v, BaseObject) and not v.__iscomplete__())

        if isinstance(fields, basestring):
            fields = (fields,)

        missing_fields = []
        if fields is None:
            # Select all fields
            if isinstance(obj, BaseObject):
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

        for key, value in self.OBJECTS.iteritems():
            if isinstance(obj, key):
                self.logger.debug(u'Fill %r with fields: %s' % (obj, missing_fields))
                return value(self, obj, missing_fields) or obj

        # Object is not supported by backend. Do not notice it to avoid flooding user.
        # That's not so bad.
        for field in missing_fields:
            setattr(obj, field, NotAvailable)

        return obj
