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

from logging import warning
import os

from weboob.core.bcall import BackendsCall
from weboob.core.backends import BackendsConfig, BackendsLoader
from weboob.core.scheduler import Scheduler
from weboob.tools.backend import BaseBackend


__all__ = ['Weboob']


class Weboob(object):
    WORKDIR = os.path.join(os.path.expanduser('~'), '.weboob')
    BACKENDS_FILENAME = 'backends'

    def __init__(self, workdir=WORKDIR, backends_filename=None, scheduler=None, storage=None):
        self.workdir = workdir
        self.backend_instances = {}

        # Scheduler
        if scheduler is None:
            scheduler = Scheduler()
        self.scheduler = scheduler

        # Create WORKDIR
        if not os.path.exists(self.workdir):
            os.mkdir(self.workdir, 0700)
        elif not os.path.isdir(self.workdir):
            warning(u'"%s" is not a directory' % self.workdir)

        # Backends loader
        self.backends_loader = BackendsLoader()

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

    def load_backends(self, caps=None, names=None, storage=None):
        loaded = {}
        if storage is None:
            storage = self.storage

        self.backends_loader.load_all()
        for backend_name, backend in self.backends_loader.loaded.iteritems():
            if caps is not None and not backend.has_caps(caps) or \
               names is not None and backend_name not in names:
                continue
            backend_instance = backend.create_instance(self, backend_name, {}, storage)
            self.backend_instances[backend_name] = loaded[backend_name] = backend_instance
        return loaded

    def load_configured_backends(self, caps=None, names=None, storage=None):
        loaded = {}
        if storage is None:
            storage = self.storage

        for instance_name, backend_name, params in self.backends_config.iter_backends():
            if '_enabled' in params and not params['_enabled']:
                continue
            backend = self.backends_loader.get_or_load_backend(backend_name)
            if backend is None:
                warning(u'Backend "%s" is referenced in ~/.weboob/backends '
                        'configuration file, but was not found. '
                        'Hint: is it installed?' % backend_name)
                continue
            if caps is not None and not backend.has_caps(caps) or \
               names is not None and instance_name not in names:
                continue
            backend_instance = backend.create_instance(self, instance_name, params, storage)
            self.backend_instances[instance_name] = loaded[instance_name] = backend_instance
        return loaded

    def unload_backends(self, names=None):
        if isinstance(names, (str,unicode)):
            names = [names]
        elif names is None:
            names = self.backend_instances.keys()

        for name in names:
            backend = self.backend_instances.pop(name)
            with backend:
                backend.deinit()

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
          the locked backend instance at first arguments, and *args and
          **kwargs.

        @param function  backend's method name, or callable object
        @param backends  list of backends to iterate on
        @param caps  iterate on backends with this caps
        @return  an iterator of results
        """
        backends = self.backend_instances.values()
        if 'backends' in kwargs:
            _backends = kwargs.pop('backends')
            if isinstance(_backends, BaseBackend):
                backends = [_backends]
            elif isinstance(_backends, (str,unicode)) and _backends:
                backends = [self.backend_instances[_backends]]
            elif isinstance(_backends, (list,tuple)):
                backends = []
                for backend in _backends:
                    if isinstance(backend, (str,unicode)):
                        try:
                            backends.append(self.backend_instances[backend])
                        except ValueError:
                            pass
                    else:
                        backends.append(backend)
            else:
                warning(u'The "backends" value isn\'t supported: %r' % _backends)

        if 'caps' in kwargs:
            caps = kwargs.pop('caps')
            backends = [backend for backend in backends if backend.has_caps(caps)]

        return BackendsCall(backends, function, *args, **kwargs)

    def schedule(self, interval, function, *args):
        return self.scheduler.schedule(interval, function, *args)

    def repeat(self, interval, function, *args):
        return self.scheduler.repeat(interval, function, *args)

    def want_stop(self):
        return self.scheduler.want_stop()

    def loop(self):
        return self.scheduler.run()
