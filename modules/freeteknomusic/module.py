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
from weboob.capabilities.base import find_object
from weboob.capabilities.audio import CapAudio, BaseAudio, Album
from weboob.capabilities.collection import CapCollection, Collection

from .browser import FreeteknomusicBrowser


__all__ = ['FreeteknomusicModule']


class FreeteknomusicModule(Module, CapAudio, CapCollection):
    NAME = 'freeteknomusic'
    DESCRIPTION = 'freeteknomusic website'
    MAINTAINER = 'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.6'

    BROWSER = FreeteknomusicBrowser

    def iter_resources(self, objs, split_path):
        if BaseAudio in objs:
            return self.browser.ls_content(split_path)
        return []

    def get_album(self, id):
        coll = find_object(self.browser.ls_content([]), id='album.%s' % id)
        if coll:
            return self._make_album(coll)

    def get_file(self, id):
        return self.browser.get_file(id)

    def get_object_method(cls, _id):
        raise NotImplementedError()

    def get_playlist(self, *args, **kwargs):
        raise NotImplementedError()

    def search_album(self, pattern, sortby=0):
        for obj in self.browser.ls_content([]):
            if isinstance(obj, Collection) and pattern in obj.title:
                yield self._make_album(obj)

    def _make_album(self, coll):
        alb = Album(coll.id)
        alb.title = coll.title
        alb.author = coll.title
        return alb

    def fill_album(self, obj, fields):
        if 'tracks_list' in fields:
            id = obj.id.replace('album.', '')
            obj.tracks_list = []
            for el in self.browser.ls_content(id.split('/')):
                if isinstance(el, BaseAudio):
                    obj.tracks_list.append(el)

    OBJECTS = {
        Album: fill_album,
    }
