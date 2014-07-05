# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon, Christophe Benz
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
from threading import Thread
try:
    import Queue
except ImportError:
    import queue as Queue

from weboob.capabilities.base import BaseObject
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

        self.responses = Queue.Queue()
        self.errors = []
        self.tasks = Queue.Queue()

        for backend in backends:
            Thread(target=self.backend_process, args=(function, args, kwargs)).start()
            self.tasks.put(backend)

    def store_result(self, backend, result):
        if isinstance(result, BaseObject):
            result.backend = backend.name
        self.responses.put((backend, result))

    def backend_process(self, function, args, kwargs):
        backend = self.tasks.get()
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
                    self.errors.append((backend, error, get_backtrace(error)))
                else:
                    self.logger.debug('%s: Called function %s returned: %r' % (backend, function, result))

                    if hasattr(result, '__iter__') and not isinstance(result, basestring):
                        # Loop on iterator
                        try:
                            for subresult in result:
                                self.store_result(backend, subresult)
                        except Exception as error:
                            self.errors.append((backend, error, get_backtrace(error)))
                    else:
                        self.store_result(backend, result)
            finally:
                self.tasks.task_done()

    def _callback_thread_run(self, callback, errback):
        while self.tasks.unfinished_tasks or not self.responses.empty():
            try:
                callback(*self.responses.get(timeout=0.1))
            except Queue.Empty:
                continue

        # Raise errors
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
        self.tasks.join()

        if self.errors:
            raise CallErrors(self.errors)

    def __iter__(self):
        while self.tasks.unfinished_tasks or not self.responses.empty():
            try:
                yield self.responses.get(timeout=0.1)
            except Queue.Empty:
                continue

        if self.errors:
            raise CallErrors(self.errors)
