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

from collections import OrderedDict

from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.capabilities.collection import CapCollection, CollectionNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value
from .browser import DailymotionBrowser

import re

__all__ = ['DailymotionModule']


class DailymotionModule(Module, CapVideo, CapCollection):
    NAME = 'dailymotion'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.6'
    DESCRIPTION = 'Dailymotion video streaming website'
    LICENSE = 'AGPLv3+'
    BROWSER = DailymotionBrowser

    resolution_choice = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        u'480': u'480p',
        u'240': u'240p',
        u'380': u'380p',
        u'720': u'720p',
        u'1080': u'1080p'
    }.iteritems())])

    format_choice = [u'm3u8', u'mp4']

    CONFIG = BackendConfig(Value('resolution', label=u'Resolution', choices=resolution_choice),
                           Value('format', label=u'Format', choices=format_choice))

    SORTBY = ['relevance', 'rated', 'visited', None]

    def create_default_browser(self):
        resolution = self.config['resolution'].get()
        format = self.config['format'].get()
        return self.create_browser(resolution=resolution, format=format)

    def get_video(self, _id):
        m = re.match('http://[w\.]*dailymotion\.com/video/(.*)', _id)
        if m:
            _id = m.group(1)

        if not _id.startswith('http'):
            return self.browser.get_video(_id)

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        return self.browser.search_videos(pattern, self.SORTBY[sortby])

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
                yield self.get_collection(objs, [u'latest'])
            if collection.split_path == [u'latest']:
                for video in self.browser.latest_videos():
                    yield video

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if BaseVideo in objs and collection.split_path == [u'latest']:
            collection.title = u'Latest Dailymotion videos'
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {BaseVideo: fill_video}
