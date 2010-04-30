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

from __future__ import with_statement

from logging import debug
from copy import copy
from threading import Thread, Event, RLock, Timer

__all__ = ['BackendsCall', 'CallErrors']

class CallErrors(Exception):
    def __init__(self, errors):
        Exception.__init__(self, "Several errors have been raised:\n%s" % ('\n'.join(['%s: %s' % (b, e) for b, e in errors])))
        self.errors = copy(errors)

    def __iter__(self):
        return self.errors.__iter__()

class Result(object):
    def __init__(self, backend, result):
        self.backend = backend
        self.result = result

    def __iter__(self):
        """
        To allow unpack.

        For example:
        >>> for backend, result in self.weboob.do(blabla)
        """
        yield self.backend
        yield self.result

class BackendsCall(object):
    def __init__(self, backends, function, *args, **kwargs):
        """
        @param backends  list of backends to call
        @param function  backends' method name, or callable object
        @param args, kwargs  arguments given to called functions
        """
        # Store if a backend is finished
        self.backends = {}
        for backend in backends:
            self.backends[backend.name] = False
        # Global mutex on object
        self.mutex = RLock()
        # Event set when every backends have give their data
        self.finish_event = Event()
        # Event set when there are new responses
        self.response_event = Event()
        # Waiting responses
        self.responses = []
        # Errors
        self.errors = []
        # Threads
        self.threads = []

        # Create jobs for each backend
        with self.mutex:
            for b in backends:
                debug('New timer for %s' % b)
                self.threads.append(Timer(0, self._caller, (b, function, args, kwargs)).start())

    def _caller(self, b, function, args, kwargs):
        debug('Hello from timer %s' % b)
        with b:
            try:
                # Call method on backend
                try:
                    if callable(function):
                        r = function(b, *args, **kwargs)
                    else:
                        r = getattr(b, function)(*args, **kwargs)
                except Exception, e:
                    with self.mutex:
                        # TODO save backtrace and/or print it here (with debug)
                        self.errors.append((b, e))
                else:
                    debug('%s: Got answer! %s' % (b, r))

                    if hasattr(r, '__iter__'):
                        # Loop on iterator
                        try:
                            for e in r:
                                # Lock mutex only in loop in case the iterator is slow
                                # (for example if backend do some parsing operations)
                                with self.mutex:
                                    self.responses.append((b,e))
                                    self.response_event.set()
                        except Exception, e:
                            with self.mutex:
                                self.errors.append((b, e))
                    else:
                        with self.mutex:
                            self.responses.append((b,r))
                            self.response_event.set()
            finally:
                with self.mutex:
                    # This backend is now finished
                    self.backends[b.name] = True
                    for finished in self.backends.itervalues():
                        if not finished:
                            return
                    self.finish_event.set()
                    self.response_event.set()

    def _callback_thread_run(self, callback, errback):
        responses = []
        while not self.finish_event.isSet():
            self.response_event.wait()
            with self.mutex:
                responses = self.responses
                self.responses = []

                # Reset event
                self.response_event.clear()

            # Consume responses
            while responses:
                callback(*responses.pop())

        if errback:
            with self.mutex:
                while self.errors:
                    errback(*self.errors.pop())

        callback(None, None)

    def callback_thread(self, callback, errback=None):
        """
        Call this method to create a thread which will callback a
        specified function everytimes a new result comes.

        When the process is over, the function will be called with
        both arguments set to None.

        The functions prototypes:
            def callback(backend, result)
            def errback(backend, error)

        """
        thread = Thread(target=self._callback_thread_run, args=(callback, errback))
        thread.start()
        return thread

    def __iter__(self):
        # Don't know how to factorize with _callback_thread_run
        responses = []
        while not self.finish_event.isSet():
            self.response_event.wait()
            with self.mutex:
                responses = self.responses
                self.responses = []

                # Reset event
                self.response_event.clear()

            # Consume responses
            while responses:
                yield Result(*responses.pop())

        # Raise errors
        with self.mutex:
            if self.errors:
                raise CallErrors(self.errors)
