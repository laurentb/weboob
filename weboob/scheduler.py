# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon, Christophe Benz
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


import logging
from threading import Timer, Event


__all__ = ['Scheduler']


class IScheduler(object):
    def schedule(self, interval, function, *args):
        raise NotImplementedError()

    def repeat(self, interval, function, *args):
        raise NotImplementedError()

    def run(self):
        raise NotImplementedError()

    def want_stop(self):
        raise NotImplementedError()

class Scheduler(IScheduler):
    def __init__(self):
        self.stop_event = Event()
        self.count = 0
        self.queue = {}

    def schedule(self, interval, function, *args):
        self.count += 1
        logging.debug('function "%s" will be called in %s seconds' % (function.__name__, interval))
        timer = Timer(interval, function, args)
        timer.start()
        self.queue[self.count] = timer
        return self.count

    def repeat(self, interval, function, *args):
        function(*args)
        return self.schedule(interval, self._repeated_cb, interval, function, args)

    def run(self):
        self.stop_event.wait()
        return True

    def want_stop(self):
        self.stop_event.set()

    def _repeated_cb(self, interval, function, args):
        function(*args)
        self.repeat(interval, function, *args)
