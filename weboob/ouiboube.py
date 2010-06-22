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
import sys

from weboob.bcall import BackendsCall, CallErrors
from weboob.modules import ModulesLoader, BackendsConfig
from weboob.scheduler import Scheduler

if sys.version_info[:2] <= (2, 5):
    import weboob.tools.property


__all__ = ['Weboob', 'CallErrors']


class Weboob(object):
    WORKDIR = os.path.join(os.path.expanduser('~'), '.weboob')
    BACKENDS_FILENAME = 'backends'

    def __init__(self, workdir=WORKDIR, backends_filename=None, scheduler=None):
        self.workdir = workdir
        self.backends = {}

        # Scheduler
        if scheduler is None:
            scheduler = Scheduler()
        self.scheduler = scheduler

        # Create WORKDIR
        if not os.path.exists(self.workdir):
            os.mkdir(self.workdir, 0700)
        elif not os.path.isdir(self.workdir):
            warning('"%s" is not a directory' % self.workdir)

        # Modules loader
        self.modules_loader = ModulesLoader()

        # Backends config
        if not backends_filename:
            backends_filename = os.path.join(self.workdir, self.BACKENDS_FILENAME)
        elif not backends_filename.startswith('/'):
            backends_filename = os.path.join(self.workdir, backends_filename)
        self.backends_config = BackendsConfig(backends_filename)

    def load_backends(self, caps=None, names=None, storage=None):
        loaded_backends = {}
        for name, _type, params in self.backends_config.iter_backends():
            try:
                module = self.modules_loader.get_or_load_module(_type)
            except KeyError:
                warning(u'Unable to find module "%s" for backend "%s"' % (_type, name))
                continue

            # Check conditions
            if (not caps is None and not module.has_caps(caps)) or \
               (not names is None and not name in names):
                continue

            try:
                self.backends[name] = module.create_backend(self, name, params, storage)
                loaded_backends[name] = self.backends[name]
            except Exception, e:
                warning(u'Unable to load "%s" backend: %s. filename=%s' % (name, e, self.backends_config.confpath))

        return loaded_backends

    def load_modules(self, caps=None, names=None, storage=None):
        loaded_backends = {}
        self.modules_loader.load()
        for name, module in self.modules_loader.modules.iteritems():
            if (caps is None or module.has_caps(caps)) and \
               (names is None or module.get_name() in names):
                try:
                    name = module.get_name()
                    self.backends[name] = module.create_backend(self, name, {}, storage)
                    loaded_backends[name] = self.backends[name]
                except Exception, e:
                    warning(u'Unable to load "%s" module as backend with no config: %s' % (name, e))
        return loaded_backends

    def iter_backends(self, caps=None):
        """
        Iter on each backends.

        Note: each backend is locked when it is returned.

        @param caps  Optional list of capabilities to select backends
        @return  iterator on selected backends.
        """
        for name, backend in sorted(self.backends.iteritems()):
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
        @return  an iterator of results
        """
        backends = list(self.iter_backends())
        return BackendsCall(backends, function, *args, **kwargs)

    def do_caps(self, caps, function, *args, **kwargs):
        """
        Do calls on loaded modules with the specified capabilities, in
        separated threads.

        See also documentation of the 'do' method.

        @param caps  list of caps or cap to select backends
        @param function  backend's method name, or callable object
        @return  an iterator of results
        """
        backends = list(self.iter_backends(caps))
        return BackendsCall(backends, function, *args, **kwargs)

    def do_backends(self, backends, function, *args, **kwargs):
        if isinstance(backends, (str,unicode)):
            backends = [backend for backend in self.iter_backends() if backend.name == backends]
        elif isinstance(backends, (list,tuple)):
            old_backends = backends
            backends = []
            for b in old_backends:
                if isinstance(b, (str,unicode)):
                    try:
                        backends.append(self.backends[self.backends.index(b)])
                    except ValueError:
                        pass
                else:
                    backends.append(b)
        return BackendsCall(backends, function, *args, **kwargs)

    def schedule(self, interval, function, *args):
        return self.scheduler.schedule(interval, function, *args)

    def repeat(self, interval, function, *args):
        return self.scheduler.repeat(interval, function, *args)

    def want_stop(self):
        return self.scheduler.want_stop()

    def loop(self):
        return self.scheduler.run()
