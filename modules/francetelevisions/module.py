# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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

from weboob.capabilities.base import empty
from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.capabilities.collection import CapCollection, CollectionNotFound, Collection
from weboob.tools.backend import Module
from weboob.tools.capabilities.video.ytdl import video_info

from .browser import PluzzBrowser


__all__ = ['PluzzModule']


class PluzzModule(Module, CapVideo, CapCollection):
    NAME = 'francetelevisions'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '2.0'
    DESCRIPTION = u'France Télévisions video website'
    LICENSE = 'AGPLv3+'
    BROWSER = PluzzBrowser

    def get_video(self, _id, video=None):
        if not video:
            video = BaseVideo(_id)

        new_video = video_info(_id)

        if not new_video:
            return

        video.ext = u'm3u8'

        for k, v in new_video.iter_fields():
            if not empty(v) and empty(getattr(video, k)):
                setattr(video, k, v)

        return video

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        return self.browser.search_videos(pattern)

    def fill_video(self, video, fields):
        if 'url' in fields:
            video = self.get_video(video.id, video)
        if video and 'thumbnail' in fields and video.thumbnail:
            video.thumbnail.data = self.browser.open(video.thumbnail.url).content
        return video

    def iter_resources(self, objs, split_path):
        if BaseVideo in objs:
            collection = self.get_collection(objs, split_path)

            if collection.path_level == 0:
                yield Collection([u'videos'], u'Vidéos')

                for category in self.browser.get_categories():
                    if category.path_level == 1:
                        yield category

            elif collection.path_level > 0 and split_path[-1] == u'videos':
                for v in self.browser.iter_videos("/".join(collection.split_path[:-1])):
                    yield v

            elif collection.path_level == 1:
                yield Collection(collection.split_path + [u'videos'], u'Vidéos')

                for category in self.browser.get_subcategories(collection.split_path[0]):
                    yield category

            elif collection.path_level == 2:
                if split_path[-1] == u'replay-videos':
                    for v in self.browser.iter_videos("/".join(collection.split_path)):
                        yield v
                else:
                    for category in self.browser.get_emissions(collection.split_path):
                        yield category

            elif collection.path_level == 3:
                for v in self.browser.iter_videos("/".join([collection.split_path[0],
                                                            collection.split_path[-1]])):
                    yield v

    def validate_collection(self, objs, collection):
        if collection.path_level <= 3:
            return

        raise CollectionNotFound(collection.split_path)

    OBJECTS = {BaseVideo: fill_video}
