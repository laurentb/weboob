# -*- coding: utf-8 -*-
#
# Copyright(C) 2014 Simon Murail
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
# XXX Licence issues?

try:
    from concurrent.futures import ThreadPoolExecutor
except ImportError:
    ThreadPoolExecutor = None

from requests import Session
from requests.adapters import DEFAULT_POOLSIZE, HTTPAdapter
from requests.compat import cookielib, OrderedDict
from requests.cookies import cookiejar_from_dict, RequestsCookieJar
from requests.models import PreparedRequest
from requests.sessions import merge_setting
from requests.structures import CaseInsensitiveDict
from requests.utils import get_netrc_auth


def merge_hooks(request_hooks, session_hooks, dict_class=OrderedDict):
    """
    Properly merges both requests and session hooks.

    This is necessary because when request_hooks == {'response': []}, the
    merge breaks Session hooks entirely.

    Backport from request so we can use it in wheezy
    """
    if session_hooks is None or session_hooks.get('response') == []:
        return request_hooks

    if request_hooks is None or request_hooks.get('response') == []:
        return session_hooks

    ret = {}
    for (k, v) in request_hooks.items():
        if v is not None:
            ret[k] = set(v).union(session_hooks.get(k, []))

    return ret


class WeboobSession(Session):
    def prepare_request(self, request):
        """Constructs a :class:`PreparedRequest <PreparedRequest>` for
        transmission and returns it. The :class:`PreparedRequest` has settings
        merged from the :class:`Request <Request>` instance and those of the
        :class:`Session`.

        :param request: :class:`Request` instance to prepare with this
                        session's settings.
        """
        cookies = request.cookies or {}

        # Bootstrap CookieJar.
        if not isinstance(cookies, cookielib.CookieJar):
            cookies = cookiejar_from_dict(cookies)

        # Merge with session cookies
        merged_cookies = RequestsCookieJar()
        merged_cookies.update(self.cookies)
        merged_cookies.update(cookies)


        # Set environment's basic authentication if not explicitly set.
        auth = request.auth
        if self.trust_env and not auth and not self.auth:
            auth = get_netrc_auth(request.url)

        p = PreparedRequest()
        p.prepare(
            method=request.method.upper(),
            url=request.url,
            files=request.files,
            data=request.data,
            headers=merge_setting(request.headers, self.headers, dict_class=CaseInsensitiveDict),
            params=merge_setting(request.params, self.params),
            auth=merge_setting(auth, self.auth),
            cookies=merged_cookies,
            hooks=merge_hooks(request.hooks, self.hooks),
        )
        return p


class FuturesSession(WeboobSession):
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
        if executor is None and ThreadPoolExecutor is not None:
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
            if not self.executor:
                raise ImportError('Please install python-concurrent.futures')

            def func(*args, **kwargs):
                resp = sup(*args, **kwargs)
                return background_callback(self, resp)

            return self.executor.submit(func, *args, **kwargs)

        return sup(*args, **kwargs)
