# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from __future__ import with_statement

from weboob.capabilities.video import ICapVideo
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import Value

from .browser import ArteBrowser
from .video import ArteVideo


__all__ = ['ArteBackend']


class ArteBackend(BaseBackend, ICapVideo):
    NAME = 'arte'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.b'
    DESCRIPTION = 'Arte French and German TV'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('lang', label='Lang of videos',
                                 choices={'fr': 'French', 'de': 'Deutsch', 'en': 'English'}, default='fr'),
                           Value('quality', label='Quality of videos', choices=['hd', 'sd'], default='hd'))
    BROWSER = ArteBrowser

    def create_default_browser(self):
        return self.create_browser(lang=self.config['lang'].get(), quality=self.config['quality'].get())

    def get_video(self, _id):
        with self.browser:
            return self.browser.get_video(_id)

    def search_videos(self, pattern=None, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False, max_results=None):
        with self.browser:
            return self.browser.search_videos(pattern)

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            with self.browser:
                video = self.browser.get_video(ArteVideo.id2url(video.id), video)
        if 'thumbnail' in fields and video.thumbnail:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)

        return video

    OBJECTS = {ArteVideo: fill_video}
