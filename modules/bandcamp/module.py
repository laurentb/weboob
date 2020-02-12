# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.tools.backend import Module
from weboob.capabilities.audio import CapAudio, BaseAudio, Album

from .browser import BandcampBrowser


__all__ = ['BandcampModule']


class BandcampModule(Module, CapAudio):
    NAME = 'bandcamp'
    DESCRIPTION = u'Bandcamp music website'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'

    BROWSER = BandcampBrowser

    def get_album(self, _id):
        _, band, album = _id.split('.')
        return self.browser.fetch_album_by_id(band, album)

    def get_audio(self, _id):
        _, band, track = _id.split('.')
        return self.browser.fetch_track_by_id(band, track)

    def search_album(self, pattern, sortby=0):
        for obj in self.browser.do_search(pattern):
            if isinstance(obj, Album):
                yield self.browser.fetch_album(obj)

    def search_audio(self, pattern, sortby=0):
        for obj in self.browser.do_search(pattern):
            if isinstance(obj, BaseAudio):
                yield self.browser.fetch_track(obj)
