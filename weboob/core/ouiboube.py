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


from __future__ import with_statement

import os

from weboob.core.bcall import BackendsCall
from weboob.core.modules import ModulesLoader, ModuleLoadError
from weboob.core.backendscfg import BackendsConfig
from weboob.core.scheduler import Scheduler
from weboob.tools.backend import BaseBackend
from weboob.tools.log import getLogger


__all__ = ['Weboob']


class Weboob(object):
    WORKDIR = os.path.join(os.path.expanduser('~'), '.weboob')
    BACKENDS_FILENAME = 'backends'

    def __init__(self, workdir=WORKDIR, backends_filename=None, scheduler=None, storage=None):
        self.logger = getLogger('weboob')
        self.workdir = workdir
        self.backend_instances = {}
        self.callbacks = {'login':   lambda backend_name, value: None,
                          'captcha': lambda backend_name, image: None,
                         }

        # Scheduler
        if scheduler is None:
            scheduler = Scheduler()
        self.scheduler = scheduler

        # Create WORKDIR
        if not os.path.exists(self.workdir):
            os.mkdir(self.workdir, 0700)
        elif not os.path.isdir(self.workdir):
            self.logger.warning(u'"%s" is not a directory' % self.workdir)

        # Backends loader
        self.modules_loader = ModulesLoader()

        # Backend instances config
        if not backends_filename:
            backends_filename = os.path.join(self.workdir, self.BACKENDS_FILENAME)
        elif not backends_filename.startswith('/'):
            backends_filename = os.path.join(self.workdir, backends_filename)
        self.backends_config = BackendsConfig(backends_filename)

        # Storage
        self.storage = storage

    def __deinit__(self):
        self.deinit()

    def deinit(self):
        self.unload_backends()

    class LoadError(Exception):
        def __init__(self, backend_name, exception):
            Exception.__init__(self, unicode(exception))
            self.backend_name = backend_name

    def load_backends(self, caps=None, names=None, modules=None, storage=None, errors=None):
        """
        Load backends.

        @param caps [tuple(ICapBase)]  load backends which implement all of caps
        @param names [tuple(unicode)]  load backends with instance name in list
        @param modules [tuple(unicode)]  load backends which module is in list
        @param storage [IStorage]  use the storage if specified
        @param errors [list]  if specified, store every errors in
        @return [dict(str,BaseBackend)]  return loaded backends
        """
        loaded = {}
        if storage is None:
            storage = self.storage

        for instance_name, module_name, params in self.backends_config.iter_backends():
            if '_enabled' in params and not params['_enabled'].lower() in ('1', 'y', 'true', 'on', 'yes') or \
               names is not None and instance_name not in names or \
               modules is not None and module_name not in modules:
                continue
            module = None
            try:
                module = self.modules_loader.get_or_load_module(module_name)
            except ModuleLoadError, e:
                self.logger.error(e)
            if module is None:
                self.logger.warning(u'Backend "%s" is referenced in ~/.weboob/backends '
                                     'configuration file, but was not found. '
                                     'Hint: is it installed?' % module_name)
                continue
            if caps is not None and not module.has_caps(caps):
                continue

            if instance_name in self.backend_instances:
                self.logger.warning(u'Oops, the backend "%s" is already loaded. Unload it before reloading...' % instance_name)
                self.unload_backends(instance_name)

            try:
                backend_instance = module.create_instance(self, instance_name, params, storage)
            except BaseBackend.ConfigError, e:
                if errors is not None:
                    errors.append(self.LoadError(instance_name, e))
            else:
                self.backend_instances[instance_name] = loaded[instance_name] = backend_instance
        return loaded

    def unload_backends(self, names=None):
        unloaded = {}
        if isinstance(names, basestring):
            names = [names]
        elif names is None:
            names = self.backend_instances.keys()

        for name in names:
            backend = self.backend_instances.pop(name)
            with backend:
                backend.deinit()
            unloaded[backend.name] = backend

        return unloaded

    def get_backend(self, name, **kwargs):
        """
        Get a backend from its name.

        It raises a KeyError if not found. If you set the 'default' parameter,
        the default value is returned instead.
        """
        try:
            return self.backend_instances[name]
        except KeyError:
            if 'default' in kwargs:
                return kwargs['default']
            else:
                raise

    def count_backends(self):
        return len(self.backend_instances)

    def iter_backends(self, caps=None):
        """
        Iter on each backends.

        Note: each backend is locked when it is returned.

        @param caps  Optional list of capabilities to select backends
        @return  iterator on selected backends.
        """
        for name, backend in sorted(self.backend_instances.iteritems()):
            if caps is None or backend.has_caps(caps):
                with backend:
                    yield backend

    def do(self, function, *args, **kwargs):
        """
        Do calls on loaded backends with specified arguments, in separated
        threads.

        This function has two modes:

        - If 'function' is a string, it calls the method with this name on
          each backends with the specified arguments;
        - If 'function' is a callable, it calls it in a separated thread with
          the locked backend instance at first arguments, and \*args and
          \*\*kwargs.

        @param function  backend's method name, or callable object
        @param backends  list of backends to iterate on
        @param caps  iterate on backends with this caps
        @param condition  a condition to validate to keep the result
        @return  the BackendsCall object (iterable)
        """
        backends = self.backend_instances.values()
        _backends = kwargs.pop('backends', None)
        if _backends is not None:
            if isinstance(_backends, BaseBackend):
                backends = [_backends]
            elif isinstance(_backends, basestring):
                if len(_backends) > 0:
                    try:
                        backends = [self.backend_instances[_backends]]
                    except (ValueError,KeyError):
                        backends = []
            elif isinstance(_backends, (list, tuple, set)):
                backends = []
                for backend in _backends:
                    if isinstance(backend, basestring):
                        try:
                            backends.append(self.backend_instances[backend])
                        except (ValueError,KeyError):
                            pass
                    else:
                        backends.append(backend)
            else:
                self.logger.warning(u'The "backends" value isn\'t supported: %r' % _backends)

        if 'caps' in kwargs:
            caps = kwargs.pop('caps')
            backends = [backend for backend in backends if backend.has_caps(caps)]
        condition = kwargs.pop('condition', None)

        # The return value MUST BE the BackendsCall instance. Please never iterate
        # here on this object, because caller might want to use other methods, like
        # wait() on callback_thread().
        # Thanks a lot.
        return BackendsCall(backends, condition, function, *args, **kwargs)

    def schedule(self, interval, function, *args):
        return self.scheduler.schedule(interval, function, *args)

    def repeat(self, interval, function, *args):
        return self.scheduler.repeat(interval, function, *args)

    def cancel(self, ev):
        return self.scheduler.cancel(ev)

    def want_stop(self):
        return self.scheduler.want_stop()

    def loop(self):
        return self.scheduler.run()
