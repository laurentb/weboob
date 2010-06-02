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

from copy import copy
import logging
from logging import debug
from threading import Thread, Event, RLock, Timer
from .tools.misc import get_backtrace

__all__ = ['BackendsCall', 'CallErrors']


class CallErrors(Exception):
    def __init__(self, errors):
        Exception.__init__(self, u'These errors have been raised in backend threads:\n%s' % (
            u'\n'.join((u' * %s: %s%s' % (backend, error, backtrace + '\n'
                                          if logging.root.level == logging.DEBUG else ''))
                       for backend, error, backtrace in errors)))
        self.errors = copy(errors)

    def __iter__(self):
        return self.errors.__iter__()


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
            for backend in backends:
                debug('Creating a new thread for %s' % backend)
                self.threads.append(Timer(0, self._caller, (backend, function, args, kwargs)).start())
            if not backends:
                self.finish_event.set()

    def _store_error(self, backend, error):
        with self.mutex:
            backtrace = get_backtrace(error)
            self.errors.append((backend, error, backtrace))

    def _store_result(self, backend, result):
        with self.mutex:
            result.id = unicode(result.id) + '@' + backend.name
            self.responses.append((backend, result))
            self.response_event.set()

    def _caller(self, backend, function, args, kwargs):
        debug('%s: Thread created successfully' % backend)
        with backend:
            try:
                # Call method on backend
                try:
                    debug('%s: Calling function %s' % (backend, function))
                    if callable(function):
                        result = function(backend, *args, **kwargs)
                    else:
                        result = getattr(backend, function)(*args, **kwargs)
                except Exception, error:
                    self._store_error(backend, error)
                else:
                    debug('%s: Called function %s returned: "%s"' % (backend, function, result))

                    if hasattr(result, '__iter__'):
                        # Loop on iterator
                        try:
                            for subresult in result:
                                # Lock mutex only in loop in case the iterator is slow
                                # (for example if backend do some parsing operations)
                                self._store_result(backend, subresult)
                        except Exception, error:
                            self._store_error(backend, error)
                    else:
                        self._store_result(backend, result)
            finally:
                with self.mutex:
                    # This backend is now finished
                    self.backends[backend.name] = True
                    for finished in self.backends.itervalues():
                        if not finished:
                            return
                    self.finish_event.set()
                    self.response_event.set()

    def _callback_thread_run(self, callback, errback):
        responses = []
        while not self.finish_event.isSet() or self.response_event.isSet():
            self.response_event.wait()
            with self.mutex:
                responses = self.responses
                self.responses = []

                # Reset event
                self.response_event.clear()

            # Consume responses
            while responses:
                callback(*responses.pop(0))

        if errback:
            with self.mutex:
                while self.errors:
                    errback(*self.errors.pop(0))

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
        while not self.finish_event.isSet() or self.response_event.isSet():
            self.response_event.wait()
            with self.mutex:
                responses = self.responses
                self.responses = []

                # Reset event
                self.response_event.clear()

            # Consume responses
            while responses:
                yield responses.pop(0)

        # Raise errors
        with self.mutex:
            if self.errors:
                raise CallErrors(self.errors)
