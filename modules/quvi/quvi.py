# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from ctypes import cdll, c_char_p, c_double, c_void_p, byref
from ctypes.util import find_library


class QuviError(Exception):
    pass


class LibQuvi04(object):
    QUVI_VERSION = 0

    QUVIOPT_FORMAT = 0
    QUVIOPT_CATEGORY = 4
    QUVI_OK = 0
    QUVI_LAST = 5

    QUVIPROP_PAGEURL = 0x100002
    QUVIPROP_PAGETITLE = 0x100003
    QUVIPROP_MEDIAID = 0x100004
    QUVIPROP_MEDIAURL = 0x100005
    QUVIPROP_FILESUFFIX = 0x100008
    #~ QUVIPROP_FORMAT = 0x10000A
    QUVIPROP_MEDIATHUMBNAILURL = 0x10000C
    QUVIPROP_MEDIACONTENTLENGTH = 0x300006
    QUVIPROP_MEDIADURATION = 0x30000D

    QUVIPROTO_HTTP = 1
    QUVIPROTO_RTMP = 8

    def __init__(self, lib=None):
        self.lib = lib
        self.qh = c_void_p()
        self.qmh = c_void_p()

    def load(self):
        path = find_library('quvi')
        if not path:
            return False

        self.lib = cdll.LoadLibrary(path)
        if self.lib is None:
            return False

        self.lib.quvi_version.restype = c_char_p
        version_str = self.lib.quvi_version(self.QUVI_VERSION)
        if version_str.startswith('v0.4'):
            return True
        else:
            return False

    def _cleanup(self):
        if self.qmh:
            self.lib.quvi_parse_close(byref(self.qmh))
            self.qmh = c_void_p()
        if self.qh:
            self.lib.quvi_close(byref(self.qh))
            self.qh = c_void_p()

    def get_info(self, url):
        try:
            return self._get_info(url)
        finally:
            self._cleanup()

    def _get_info(self, url):
        status = self.lib.quvi_init(byref(self.qh))
        self._assert_ok(status)

        status = self.lib.quvi_setopt(self.qh, self.QUVIOPT_FORMAT, 'best')
        self._assert_ok(status)

        status = self.lib.quvi_parse(self.qh, c_char_p(url), byref(self.qmh))
        self._assert_ok(status)

        info = {}
        info['url'] = self._get_str(self.QUVIPROP_MEDIAURL)
        info['title'] = self._get_str(self.QUVIPROP_PAGETITLE)
        info['suffix'] = self._get_str(self.QUVIPROP_FILESUFFIX)
        info['page'] = self._get_str(self.QUVIPROP_PAGEURL) # uncut!
        info['media_id'] = self._get_str(self.QUVIPROP_MEDIAID)
        info['thumbnail'] = self._get_str(self.QUVIPROP_MEDIATHUMBNAILURL)
        info['duration'] = self._get_double(self.QUVIPROP_MEDIADURATION)
        info['size'] = self._get_double(self.QUVIPROP_MEDIACONTENTLENGTH)

        return info

    def _assert_ok(self, status):
        if status != self.QUVI_OK:
            self.lib.quvi_strerror.restype = c_char_p
            c_msg = self.lib.quvi_strerror(self.qh, status)
            raise QuviError(c_msg)

    def _get_str(self, prop):
        c_value = c_char_p()
        status = self.lib.quvi_getprop(self.qmh, prop, byref(c_value))
        self._assert_ok(status)

        return c_value.value

    def _get_double(self, prop):
        c_value = c_double()
        status = self.lib.quvi_getprop(self.qmh, prop, byref(c_value))
        self._assert_ok(status)

        return c_value.value


LibQuvi = LibQuvi04
