# -*- coding: utf-8 -*-

# Copyright(C) 2015 Guilhem Bonnefille
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
from weboob.capabilities.collection import CapCollection, Collection
from weboob.tools.backend import Module

from .browser import RmllBrowser
from .video import RmllVideo


__all__ = ['RmllModule']


class RmllModule(Module, CapVideo, CapCollection):
    NAME = 'rmll'
    MAINTAINER = u'Guyou'
    EMAIL = 'guilhem.bonnefille@gmail.com'
    VERSION = '2.1'
    DESCRIPTION = 'Videos from RMLL'
    LICENSE = 'AGPLv3+'

    BROWSER = RmllBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_video(self, _id):
        self.logger.debug("Getting video for %s", _id)
        return self.browser.get_video(_id)

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        return self.browser.search_videos(pattern)

    def fill_video(self, video, fields):
        self.logger.debug("Fill video %s for fields %s", video.id, fields)
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            video = self.browser.get_video(video.id, video)
        if 'thumbnail' in fields and video and video.thumbnail:
            video.thumbnail.data = self.browser.open(video.thumbnail.url).content

        return video

    def iter_resources(self, objs, split_path):
        if BaseVideo in objs:
            if len(split_path) == 0:
                # Add fake Collection
                yield Collection(['latest'], u'Latest')
            if len(split_path) == 1 and split_path[0] == 'latest':
                for video in self.browser.get_latest_videos():
                    yield video
            else:
                channel_videos = self.browser.get_channel_videos(split_path)
                if channel_videos:
                    for content in channel_videos:
                        yield content

    OBJECTS = {RmllVideo: fill_video}
