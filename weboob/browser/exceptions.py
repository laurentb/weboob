# -*- coding: utf-8 -*-

# Copyright(C) 2014 Laurent Bachelier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

import datetime

from dateutil.relativedelta import relativedelta
from requests.exceptions import HTTPError
from weboob.exceptions import (
    BrowserHTTPError, BrowserHTTPNotFound, BrowserUnavailable,
)


class HTTPNotFound(HTTPError, BrowserHTTPNotFound):
    pass


class ClientError(HTTPError, BrowserHTTPError):
    pass


class ServerError(HTTPError, BrowserHTTPError):
    pass


class LoggedOut(Exception):
    pass


class BrowserTooManyRequests(BrowserUnavailable):
    """
    Client tries to perform too many requests within a certain timeframe.
    The module should set the next_try if possible, else it is set to 24h.
    """
    def __init__(self, next_try=None):
        if next_try is None:
            next_try = datetime.datetime.now() + relativedelta(days=1)

        self.next_try = next_try

    def __str__(self):
        return 'Too many requests, next_try set %s' % self.next_try
