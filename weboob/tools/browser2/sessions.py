# -*- coding: utf-8 -*-
#
# Copyright(C) 2014      smurail
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

# Inspired by: https://github.com/ross/requests-futures/blob/master/requests_futures/sessions.py
# XXX Licence issues ?

from concurrent.futures import ThreadPoolExecutor
from requests import Session
from requests.adapters import DEFAULT_POOLSIZE, HTTPAdapter

class FuturesSession(Session):

    def __init__(self, executor=None, max_workers=2, *args, **kwargs):
        """Creates a FuturesSession

        Notes
        ~~~~~

        * ProcessPoolExecutor is not supported b/c Response objects are
          not picklable.

        * If you provide both `executor` and `max_workers`, the latter is
          ignored and provided executor is used as is.
        """
        super(FuturesSession, self).__init__(*args, **kwargs)
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=max_workers)
            # set connection pool size equal to max_workers if needed
            if max_workers > DEFAULT_POOLSIZE:
                adapter_kwargs = dict(pool_connections=max_workers,
                                      pool_maxsize=max_workers)
                self.mount('https://', HTTPAdapter(**adapter_kwargs))
                self.mount('http://', HTTPAdapter(**adapter_kwargs))

        self.executor = executor

    def send(self, *args, **kwargs):
        """Maintains the existing api for :meth:`Session.send`

        Used by :meth:`request` and thus all of the higher level methods

        If background_callback param is defined, request is processed in a
        thread, calling background_callback and returning it's result when
        request has been processed. If background_callback is not defined,
        request is processed as usual, in a blocking way.
        """
        sup = super(FuturesSession, self).send

        background_callback = kwargs.pop('background_callback', None)
        if background_callback:
            def func(*args, **kwargs):
                resp = sup(*args, **kwargs)
                return background_callback(self, resp)

            return self.executor.submit(func, *args, **kwargs)

        return sup(*args, **kwargs)
