# -*- coding: utf-8 -*-

# Copyright(C) 2013      franek
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
from weboob.capabilities.collection import CapCollection, CollectionNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import ArretSurImagesBrowser
from .video import ArretSurImagesVideo

__all__ = ['ArretSurImagesModule']


class ArretSurImagesModule(Module, CapVideo, CapCollection):
    NAME = 'arretsurimages'
    DESCRIPTION = u'arretsurimages website'
    MAINTAINER = u'franek'
    EMAIL = 'franek@chicour.net'
    VERSION = '1.4'

    CONFIG = BackendConfig(ValueBackendPassword('login',    label='email', masked=False),
                           ValueBackendPassword('password', label='Password'))
    BROWSER = ArretSurImagesBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get(), get_home=False)

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        with self.browser:
            return self.browser.search_videos(pattern)
#        raise UserError('Search does not work on ASI website, use ls latest command')

    def get_video(self, _id):
        if _id.startswith('http://') and not _id.startswith('http://www.arretsurimages.net'):
            return None
        with self.browser:
            return self.browser.get_video(_id)

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            with self.browser:
                video = self.browser.get_video(ArretSurImagesVideo.id2url(video.id), video)
        if 'thumbnail' in fields and video.thumbnail:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)

        return video

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
            collection.title = u'Latest ArretSurImages videos'
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {ArretSurImagesVideo: fill_video}
