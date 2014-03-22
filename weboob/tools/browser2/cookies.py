# -*- coding: utf-8 -*-
# Copyright(C) 2014 Laurent Bachelier
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

import requests.cookies
import cookielib


__all__ = ['WeboobCookieJar']


class WeboobCookieJar(requests.cookies.RequestsCookieJar):
    @classmethod
    def from_cookiejar(klass, cj):
        """
        Create a WeboobCookieJar from another CookieJar instance.
        """
        return requests.cookies.merge_cookies(klass(), cj)

    def export(self, filename):
        """
        Export all cookies to a file, regardless of expiration, etc.
        """
        cj = requests.cookies.merge_cookies(cookielib.LWPCookieJar(), self)
        cj.save(filename, ignore_discard=True, ignore_expires=True)

    def _cookies_from_attrs_set(self, attrs_set, request):
        for tup in self._normalized_cookie_tuples(attrs_set):
            cookie = self._cookie_from_cookie_tuple(tup, request)
            if cookie:
                yield cookie

    def make_cookies(self, response, request):
        """Return sequence of Cookie objects extracted from response object."""
        # get cookie-attributes for RFC 2965 and Netscape protocols
        headers = response.info()
        rfc2965_hdrs = headers.getheaders("Set-Cookie2")
        ns_hdrs = headers.getheaders("Set-Cookie")

        rfc2965 = self._policy.rfc2965
        netscape = self._policy.netscape

        if netscape:
            for cookie in self._cookies_from_attrs_set(cookielib.parse_ns_headers(ns_hdrs), request):
                self._process_rfc2109_cookies([cookie])
                yield cookie

        if rfc2965:
            for cookie in self._cookies_from_attrs_set(cookielib.split_header_words(rfc2965_hdrs), request):
                yield cookie

    def copy(self):
        new_cj = type(self)()
        new_cj.update(self)
        return new_cj
