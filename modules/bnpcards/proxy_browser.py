# -*- coding: utf-8 -*-

# Copyright(C) 2017      Budget Insight
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


from functools import wraps

from .browser import BnpcartesentrepriseBrowser
from .corporate.browser import BnpcartesentrepriseCorporateBrowser


class ProxyBrowser(object):
    def __init__(self, *args, **kwargs):
        super(ProxyBrowser, self).__init__()
        self._browser_args = args
        self._browser_kwargs = kwargs

        self._browser = BnpcartesentrepriseBrowser(*args, **kwargs)

    def __getattr__(self, attr):
        val = getattr(self._browser, attr)
        if not callable(val):
            return val

        @wraps(val)
        def wrapper(*args, **kwargs):
            try:
                return val(*args, **kwargs)
            except BnpcartesentrepriseBrowser.CorporateCard:
                self._browser = BnpcartesentrepriseCorporateBrowser(*self._browser_args, **self._browser_kwargs)
                val2 = getattr(self._browser, attr)
                return val2(*args, **kwargs)

        return wrapper

