# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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


from weboob.tools.backend import BaseBackend
from weboob.capabilities.radio import ICapRadio, Radio, Stream, Emission
from weboob.capabilities.video import ICapVideo, BaseVideo
from weboob.capabilities.collection import ICapCollection
from .browser import GroovesharkBrowser

__all__ = ['GroovesharkBackend']

class GroovesharkBackend(BaseBackend, ICapVideo, ICapCollection):
    NAME = 'grooveshark'
    DESCRIPTION = u'grooveshark website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '0.g'
    LICENSE = 'AGPLv3+'

    BROWSER = GroovesharkBrowser

    def fill_video(self, video, fields):
        if 'url' in fields:
            with self.browser:
                video.url = unicode(self.browser.get_stream_url_from_song_id(video.id))
        if 'thumbnail' in fields and video.thumbnail:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)

    def search_videos(self, pattern, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False, max_results=10):
        with self.browser:
            for video in self.browser.search_videos(pattern, max_results):
               yield video

    def get_video(self, video):
        with self.browser:
            return self.browser.fill_stream_list(video)

    OBJECTS = {BaseVideo: fill_video}
