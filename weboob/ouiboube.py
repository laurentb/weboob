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
import sched
import time

from weboob.modules import ModulesLoader

class Weboob:
    WORKDIR = os.path.join(os.path.expanduser('~'), '.weboob')
    BACKENDS_FILENAME = 'backends'

    def __init__(self, app_name, workdir=WORKDIR):
        self.app_name = app_name
        self.workdir = workdir
        self.backends = {}
        self.scheduler = sched.scheduler(time.time, time.sleep)

        self.modules_loader = ModulesLoader()
        self.modules_loader.load()

    def get_backends_filename(self):
        return os.path.join(self.workdir, self.BACKENDS_FILENAME)

    def load_backends(self, caps=None, names=None):
        self.backends.update(self.modules_loader.load_backends(self.get_backends_filename(), caps, names))

    def load_modules(self, caps=None, names=None):
        self.backends.update(self.modules_loader.load_modules_as_backends(caps, names))

    def iter_backends(self, caps=None):
        for name, backend in self.backends.iteritems():
            if caps is None or backend.has_caps(caps):
                yield (name, backend)

    def schedule(self, interval, function, *args):
        self.scheduler.enter(interval, 1, function, args)

    def loop(self):
        self.scheduler.run()
