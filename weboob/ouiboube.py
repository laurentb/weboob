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

import os

from weboob.modules import ModulesLoader
from weboob.scheduler import Scheduler

class Weboob:
    WORKDIR = os.path.join(os.path.expanduser('~'), '.weboob')
    BACKENDS_FILENAME = 'backends'

    def __init__(self, app_name, workdir=WORKDIR, scheduler=None):
        self.app_name = app_name
        self.workdir = workdir
        self.backends = {}

        if scheduler is None:
            scheduler = Scheduler()
        self.scheduler = scheduler

        self.modules_loader = ModulesLoader()
        self.modules_loader.load()

    def get_backends_filename(self):
        return os.path.join(self.workdir, self.BACKENDS_FILENAME)

    def load_backends(self, caps=None, names=None):
        self.backends.update(self.modules_loader.load_backends(self.get_backends_filename(), caps, names))
        return self.backends

    def load_modules(self, caps=None, names=None):
        self.backends.update(self.modules_loader.load_modules_as_backends(caps, names))
        return self.backends

    def iter_backends(self, caps=None):
        for name, backend in self.backends.iteritems():
            if caps is None or backend.has_caps(caps):
                yield (name, backend)

    def schedule(self, interval, function, *args):
        return self.scheduler.schedule(interval, function, *args)

    def repeat(self, interval, function, *args):
        return self.scheduler.repeat(interval, function, *args)

    def loop(self):
        return self.scheduler.run()
