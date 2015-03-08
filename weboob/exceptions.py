# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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



class BrowserIncorrectPassword(Exception):
    pass


class BrowserForbidden(Exception):
    pass


class BrowserBanned(BrowserIncorrectPassword):
    pass


class BrowserPasswordExpired(BrowserIncorrectPassword):
    pass


class BrowserUnavailable(Exception):
    pass


class BrowserQuestion(BrowserIncorrectPassword):
    """
    When raised by a browser,
    """
    def __init__(self, *fields):
        self.fields = fields


class BrowserHTTPNotFound(BrowserUnavailable):
    pass


class BrowserHTTPError(BrowserUnavailable):
    pass


class BrowserSSLError(BrowserUnavailable):
    pass


class ParseError(Exception):
    pass


class FormFieldConversionWarning(UserWarning):
    """
    A value has been set to a form's field and has been implicitly converted.
    """
