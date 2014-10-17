# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
# Copyright(C) 2012 François Revol
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


from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.tools.backend import Module
from weboob.capabilities.collection import CapCollection, CollectionNotFound

from .browser import VimeoBrowser

import re

__all__ = ['VimeoModule']


class VimeoModule(Module, CapVideo, CapCollection):
    NAME = 'vimeo'
    MAINTAINER = u'François Revol'
    EMAIL = 'revol@free.fr'
    VERSION = '1.1'
    DESCRIPTION = 'Vimeo video streaming website'
    LICENSE = 'AGPLv3+'
    BROWSER = VimeoBrowser

    SORTBY = ['relevance', 'rating', 'views', 'time']

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        return self.browser.search_videos(pattern, self.SORTBY[sortby])

    def get_video(self, _id):
        return self.browser.get_video(self.parse_id(_id))

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            video = self.browser.get_video(video.id, video)
        if 'thumbnail' in fields and video.thumbnail:
            video.thumbnail.data = self.browser.open(video.thumbnail.url).content

        return video

    def parse_id(self, _id):
        m = re.match('https?://vimeo.com/(.*)', _id)
        if m:
            return m.group(1)
        return _id

    def iter_resources(self, objs, split_path):
        if BaseVideo in objs:
            collection = self.get_collection(objs, split_path)
            if collection.path_level == 0:
                yield self.get_collection(objs, [u'latest'])
            if collection.split_path == [u'latest']:
                for video in self.browser.latest_videos():
                    yield video

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if BaseVideo in objs and collection.split_path == [u'latest']:
            collection.title = u'Latest Vimeo videos'
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {BaseVideo: fill_video}
