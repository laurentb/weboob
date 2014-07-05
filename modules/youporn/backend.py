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




from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.tools.backend import BaseBackend
from weboob.capabilities.collection import CapCollection, CollectionNotFound

from .browser import YoupornBrowser
from .video import YoupornVideo


__all__ = ['YoupornBackend']


class YoupornBackend(BaseBackend, CapVideo, CapCollection):
    NAME = 'youporn'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.j'
    DESCRIPTION = 'YouPorn pornographic video streaming website'
    LICENSE = 'AGPLv3+'
    BROWSER = YoupornBrowser

    def get_video(self, _id):
        with self.browser:
            return self.browser.get_video(_id)

    SORTBY = ['relevance', 'rating', 'views', 'time']

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        if not nsfw:
            return set()
        with self.browser:
            return self.browser.search_videos(pattern, self.SORTBY[sortby])

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            with self.browser:
                video = self.browser.get_video(YoupornVideo.id2url(video.id), video)
        if 'thumbnail' in fields and video.thumbnail:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)

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
            collection.title = u'Latest YouPorn videos (NSFW)'
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {YoupornVideo: fill_video}
