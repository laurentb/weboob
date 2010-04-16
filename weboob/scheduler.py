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

import sched
import time


__all__ = ['Scheduler']


class Scheduler(object):
    def __init__(self):
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.running = False

    def schedule(self, interval, function, *args):
        return self.scheduler.enter(interval, 1, function, args)

    def repeat(self, interval, function, *args):
        return self.scheduler.enter(interval, 1, self._repeated_cb, (interval, function, args))

    def run(self):
        self.running = True
        while self.running:
            self.scheduler.run()
            if not self.scheduler.queue:
                self.scheduler.delayfunc(0.001)
        return True

    def want_stop(self):
        self.running = False

    def _repeated_cb(self, interval, func, args):
        func(*args)
        self.repeat(interval, func, *args)
