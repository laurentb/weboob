# -*- coding: utf-8 -*-

# Copyright(C) 2016 Roger Philibert
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
from weboob.capabilities.collection import CapCollection, CollectionNotFound
from weboob.tools.backend import Module

from .browser import PornhubBrowser


__all__ = ['PornhubModule']


class PornhubModule(Module, CapVideo, CapCollection):
    NAME = 'pornhub'
    MAINTAINER = u'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    VERSION = '1.5'
    DESCRIPTION = 'Pornhub pornographic video streaming website'
    LICENSE = 'AGPLv3+'
    BROWSER = PornhubBrowser

    def get_video(self, _id):
        video = self.browser.get_video(_id)
        return video

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        if not nsfw:
            return set()
        return self.browser.search_videos(pattern)

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            video = self.browser.get_video(video.id, video)
        if 'thumbnail' in fields and video.thumbnail:
            video.thumbnail.data = self.browser.open(video.thumbnail.url).content

        return video

    def iter_resources(self, objs, split_path):
        if BaseVideo in objs:
            collection = self.get_collection(objs, split_path)
            if collection.path_level == 0:
                yield self.get_collection(objs, [u'latest_nsfw'])
            if collection.split_path == [u'latest_nsfw']:
                for video in self.browser.latest_videos():
                    yield video

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if BaseVideo in objs and collection.split_path == [u'latest_nsfw']:
            collection.title = u'Latest Pornhub videos (NSFW)'
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {BaseVideo: fill_video}
