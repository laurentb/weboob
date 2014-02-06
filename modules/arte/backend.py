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


import re

from weboob.capabilities.video import ICapVideo, BaseVideo
from weboob.capabilities.collection import ICapCollection, CollectionNotFound, Collection
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import Value

from .browser import ArteBrowser
from .video import ArteVideo, ArteLiveVideo


__all__ = ['ArteBackend']


class ArteBackend(BaseBackend, ICapVideo, ICapCollection):
    NAME = 'arte'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '0.i'
    DESCRIPTION = 'Arte French and German TV'
    LICENSE = 'AGPLv3+'

    order = {'AIRDATE_DESC': 'Date',
             'VIEWS': 'Views',
             'ALPHA': 'Alphabetic',
             'LAST_CHANCE': 'Last chance'
             }

    CONFIG = BackendConfig(Value('lang', label='Lang of videos',
                                 choices={'fr': 'French', 'de': 'Deutsch', 'en': 'English'}, default='fr'),
                           Value('order', label='Sort order', choices=order, default='AIRDATE_DESC'),
                           Value('quality', label='Quality of videos', choices=['hd', 'sd', 'md', 'ed'], default='hd'))

    TRANSLATION  = {'fr': 'F',
                    'en': 'F',
                    'de': 'D',
                    'hd': 'HQ',
                    'md': 'MQ',
                    'sd': 'SQ',
                    'eq': 'EQ'
                    }

    BROWSER = ArteBrowser

    def create_default_browser(self):
        return self.create_browser(lang=self.TRANSLATION[self.config['lang'].get()],
                                   quality=self.TRANSLATION[self.config['quality'].get()],
                                   order=self.config['order'].get())

    def parse_id(self, _id):
        m = re.match('^(\w+)\.(.*)', _id)
        if m:
            return m.groups()

        m = re.match('https?://www.arte.tv/guide/\w+/(?P<id>.+)/(.*)', _id)
        if m:
            return 'program', m.group(1)

        m = re.match('https?://concert.arte.tv/(\w+)/(.*)', _id)
        if m:
            return 'live', '/%s/%s' % (m.group(1), m.group(2))

        return 'videos', _id

    def get_video(self, _id):
        with self.browser:
            site, _id = self.parse_id(_id)

            if site == 'live':
                return self.browser.get_live_video(_id)

            elif site == 'program':
                return self.browser.get_video_from_program_id(_id)

            else:
                return self.browser.get_video(_id)

    def search_videos(self, pattern, sortby=ICapVideo.SEARCH_RELEVANCE, nsfw=False):
        with self.browser:
            return self.browser.search_videos(pattern)

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            # if we don't want only the thumbnail, we probably want also every fields
            with self.browser:
                site, _id = self.parse_id(video.id)

                if isinstance(video, ArteVideo):
                    video = self.browser.get_video(_id, video)
                if isinstance(video, ArteLiveVideo):
                    video = self.browser.get_live_video(_id, video)
        if 'thumbnail' in fields and video and video.thumbnail:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)

        return video

    def iter_resources(self, objs, split_path):
        with self.browser:
            if BaseVideo in objs:
                collection = self.get_collection(objs, split_path)
                if collection.path_level == 0:
                    yield Collection([u'arte-latest'], u'Latest Arte videos')
                    yield Collection([u'arte-live'], u'Arte Web Live videos')
                if collection.path_level == 1:
                    if collection.split_path == [u'arte-latest']:
                        for video in self.browser.latest_videos():
                            yield video
                    if collection.split_path == [u'arte-live']:
                        for categorie in self.browser.get_arte_live_categories():
                            yield categorie
                if collection.path_level == 2:
                    if collection.split_path[0] == u'arte-live':
                        for video in self.browser.live_videos(collection.basename):
                            yield video

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if BaseVideo in objs and (collection.split_path == [u'arte-latest'] or collection.split_path == [u'arte-live']):
            return
        if BaseVideo in objs and collection.path_level == 2 and collection.split_path[0] == u'arte-live':
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {ArteVideo: fill_video, ArteLiveVideo: fill_video }
