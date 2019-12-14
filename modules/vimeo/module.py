# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
# Copyright(C) 2012 François Revol
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

from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.tools.backend import Module
from weboob.tools.capabilities.video.ytdl import video_info


from .browser import VimeoBrowser


__all__ = ['VimeoModule']


class VimeoModule(Module, CapVideo):
    NAME = 'vimeo'
    MAINTAINER = u'François Revol'
    EMAIL = 'revol@free.fr'
    VERSION = '1.6'
    DESCRIPTION = 'Vimeo video streaming website'
    LICENSE = 'AGPLv3+'
    BROWSER = VimeoBrowser

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        return self.browser.search_videos(pattern, sortby, nsfw)

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            video = video_info(self.browser.absurl('/%s' % video.id, base=True))

        if 'thumbnail' in fields and video and video.thumbnail:
            video.thumbnail.data = self.browser.open(video.thumbnail.url).content

        return video

    OBJECTS = {BaseVideo: fill_video}
