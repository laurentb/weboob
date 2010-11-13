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


from __future__ import with_statement

from threading import Timer, Event, RLock, _Timer
from weboob.tools.log import getLogger


__all__ = ['Scheduler']


class IScheduler(object):
    def schedule(self, interval, function, *args):
        raise NotImplementedError()

    def repeat(self, interval, function, *args):
        raise NotImplementedError()

    def cancel(self, ev):
        raise NotImplementedError()

    def run(self):
        raise NotImplementedError()

    def want_stop(self):
        raise NotImplementedError()

class RepeatedTimer(_Timer):
    def run(self):
        while not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)
        self.finished.set()

class Scheduler(IScheduler):
    def __init__(self):
        self.logger = getLogger('scheduler')
        self.mutex = RLock()
        self.stop_event = Event()
        self.count = 0
        self.queue = {}

    def schedule(self, interval, function, *args):
        return self._schedule(Timer, interval, self._schedule_callback, function, *args)

    def repeat(self, interval, function, *args):
        return self._schedule(RepeatedTimer, interval, self._repeat_callback, function, *args)

    def _schedule(self, klass, interval, meta_func, function, *args):
        if self.stop_event.is_set():
            return

        with self.mutex:
            self.count += 1
            self.logger.debug('function "%s" will be called in %s seconds' % (function.__name__, interval))
            timer = klass(interval, meta_func, (self.count, interval, function, args))
            self.queue[self.count] = timer
            timer.start()
            return self.count

    def _schedule_callback(self, count, interval, function, args):
        with self.mutex:
            self.queue.pop(count)
        return function(*args)

    def _repeat_callback(self, count, interval, function, args):
        function(*args)
        with self.mutex:
            try:
                e = self.queue[count]
            except KeyError:
                return
            else:
                self.logger.debug('function "%s" will be called in %s seconds' % (function.__name__, e.interval))

    def cancel(self, ev):
        with self.mutex:
            try:
                e = self.queue.pop(ev)
            except KeyError:
                return False
            e.cancel()
            self.logger.debug('scheduled function "%s" is canceled' % e.function)
            return True

    def _wait_to_stop(self):
        self.want_stop()
        with self.mutex:
            for e in self.queue.itervalues():
                e.cancel()
                e.join()
            self.queue = {}

    def run(self):
        try:
            while 1:
                self.stop_event.wait(0.1)
        except KeyboardInterrupt:
            self._wait_to_stop()
            raise
        else:
            self._wait_to_stop()
        return True

    def want_stop(self):
        self.stop_event.set()
        with self.mutex:
            for t in self.queue.itervalues():
                t.cancel()
                # Contrary to _wait_to_stop(), don't call t.join
                # because want_stop() have to be non-blocking.
            self.queue = {}
