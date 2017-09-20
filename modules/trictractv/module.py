# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
# Copyright(C) 2012  Benjamin Drieu
#
# This file is *not yet* part of weboob.
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


from weboob.capabilities.video import CapVideo
from weboob.tools.backend import Module

from .browser import TricTracTVBrowser
from .video import TricTracTVVideo


__all__ = ['TricTracTVModule']


class TricTracTVModule(Module, CapVideo):
    NAME = 'trictractv'
    MAINTAINER = u'Benjamin Drieu'
    EMAIL = 'benjamin@drieu.org'
    VERSION = '1.4'
    DESCRIPTION = u'TricTrac.tv video website'
    LICENSE = 'AGPLv3+'
    BROWSER = TricTracTVBrowser

    def get_video(self, _id):
        with self.browser:
            return self.browser.get_video(_id)

    def search_videos(self, pattern=None, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        with self.browser:
            return self.browser.search_videos(pattern)

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            with self.browser:
                video = self.browser.get_video(TricTracTVVideo.id2url(video.id), video)
        if 'thumbnail' in fields and video.thumbnail:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)

        return video

    OBJECTS = {TricTracTVVideo: fill_video}
