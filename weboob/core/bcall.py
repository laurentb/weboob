# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon, Christophe Benz
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




from copy import copy
from threading import Thread, Event, RLock, Timer

from weboob.capabilities.base import CapBaseObject
from weboob.tools.misc import get_backtrace
from weboob.tools.log import getLogger


__all__ = ['BackendsCall', 'CallErrors']


class CallErrors(Exception):
    def __init__(self, errors):
        msg = 'Errors during backend calls:\n' + \
                '\n'.join(['Module(%r): %r\n%r\n' % (backend, error, backtrace)
                           for backend, error, backtrace in errors])

        Exception.__init__(self, msg)
        self.errors = copy(errors)

    def __iter__(self):
        return self.errors.__iter__()


class BackendsCall(object):
    def __init__(self, backends, function, *args, **kwargs):
        """
        :param backends: List of backends to call
        :type backends: list[:class:`BaseBackend`]
        :param function: backends' method name, or callable object.
        :type function: :class:`str` or :class:`callable`
        """
        self.logger = getLogger('bcall')
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
                self.threads.append(Timer(0, self._caller, (backend, function, args, kwargs)).start())
            if not backends:
                self.finish_event.set()

    def _store_error(self, backend, error):
        with self.mutex:
            backtrace = get_backtrace(error)
            self.errors.append((backend, error, backtrace))

    def _store_result(self, backend, result):
        with self.mutex:
            if isinstance(result, CapBaseObject):
                result.backend = backend.name
            self.responses.append((backend, result))
            self.response_event.set()

    def _caller(self, backend, function, args, kwargs):
        with backend:
            try:
                # Call method on backend
                try:
                    self.logger.debug('%s: Calling function %s' % (backend, function))
                    if callable(function):
                        result = function(backend, *args, **kwargs)
                    else:
                        result = getattr(backend, function)(*args, **kwargs)
                except Exception as error:
                    self.logger.debug('%s: Called function %s raised an error: %r' % (backend, function, error))
                    self._store_error(backend, error)
                else:
                    self.logger.debug('%s: Called function %s returned: %r' % (backend, function, result))

                    if hasattr(result, '__iter__') and not isinstance(result, basestring):
                        # Loop on iterator
                        try:
                            for subresult in result:
                                # Lock mutex only in loop in case the iterator is slow
                                # (for example if backend do some parsing operations)
                                self._store_result(backend, subresult)
                        except Exception as error:
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
                    self.response_event.set()
                    self.finish_event.set()

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

    def wait(self):
        self.finish_event.wait()

        with self.mutex:
            if self.errors:
                raise CallErrors(self.errors)

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
