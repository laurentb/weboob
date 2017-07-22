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
from collections import OrderedDict

from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.capabilities.collection import CapCollection, CollectionNotFound, Collection
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value
from weboob.exceptions import BrowserHTTPSDowngrade

from .browser import ArteBrowser
from .video import ArteVideo, ArteSiteVideo, VERSION_VIDEO, FORMATS, LANG, QUALITY, SITE


__all__ = ['ArteModule']


class ArteModule(Module, CapVideo, CapCollection):
    NAME = 'arte'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '1.3'
    DESCRIPTION = 'Arte French and German TV'
    LICENSE = 'AGPLv3+'

    order = {'AIRDATE_DESC': 'Date',
             'VIEWS': 'Views',
             'ALPHA': 'Alphabetic',
             'LAST_CHANCE': 'Last chance'
             }

    versions_choice = OrderedDict([(k, u'%s' % (v.get('label'))) for k, v in VERSION_VIDEO.items])
    format_choice = OrderedDict([(k, u'%s' % (v)) for k, v in FORMATS.items])
    lang_choice = OrderedDict([(k, u'%s' % (v.get('label'))) for k, v in LANG.items])
    quality_choice = [u'%s' % (k) for k, v in QUALITY.items]

    CONFIG = BackendConfig(Value('lang', label='Lang of videos', choices=lang_choice, default='FRENCH'),
                           Value('order', label='Sort order', choices=order, default='AIRDATE_DESC'),
                           Value('quality', label='Quality of videos', choices=quality_choice, default='HD'),
                           Value('format', label='Format of videos', choices=format_choice, default=FORMATS.HTTP_MP4),
                           Value('version', label='Version of videos', choices=versions_choice))

    BROWSER = ArteBrowser

    def create_default_browser(self):
        return self.create_browser(lang=self.config['lang'].get(),
                                   quality=self.config['quality'].get(),
                                   order=self.config['order'].get(),
                                   format=self.config['format'].get(),
                                   version=self.config['version'].get())

    def parse_id(self, _id):
        sites = '|'.join(k.get('id') for k in SITE.values)
        m = re.match('^(%s)\.(.*)' % sites, _id)
        if m:
            return m.groups()

        m = re.match('https?://www.arte.tv/guide/\w+/(?P<id>.+)/(.*)', _id)
        if m:
            return SITE.PROGRAM.get('id'), m.group(1)

        m = re.match('https?://(%s).arte.tv/(\w+)/(.*)' % (sites), _id)
        if m:
            return m.group(1), '/%s/%s' % (m.group(2), m.group(3))

        if not _id.startswith('http'):
            return 'videos', _id

        return None, None

    def get_video(self, _id):
        site, _id = self.parse_id(_id)

        if not (site and _id):
            return None

        if site in [value.get('id') for value in SITE.values]:
            _site = (value for value in SITE.values if value.get('id') == site).next()
            return getattr(self.browser, _site.get('video'))(_id)

        else:
            return self.browser.get_video(_id)

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        return self.browser.search_videos(pattern)

    def fill_arte_video(self, video, fields):
        if fields != ['thumbnail']:
            video = self.browser.get_video(video.id, video)

        if 'thumbnail' in fields and video and video.thumbnail:
            video.thumbnail.data = self.browser.open(video.thumbnail.url).content

        if 'url' in fields and not video.url:
            video.ext, video.url = self.browser.fetch_url(video.id)

        return video

    def fill_site_video(self, video, fields):
        if fields != ['thumbnail']:
            for site in SITE.values:
                m = re.match('%s\.(.*)' % site.get('id'), video.id)
                if m:
                    video = getattr(self.browser, site.get('video'))(m.group(1), video)
                    break

        if 'thumbnail' in fields and video and video.thumbnail:
            try:
                video.thumbnail.data = self.browser.open(video.thumbnail.url).content
            except BrowserHTTPSDowngrade:
                pass

        return video

    def iter_resources(self, objs, split_path):
        if BaseVideo in objs:
            collection = self.get_collection(objs, split_path)
            if collection.path_level == 0:
                yield Collection([u'arte-latest'], u'Latest Arte videos')
                for site in SITE.values:
                    yield Collection([site.get('id')], site.get('label'))
            if collection.path_level == 1:
                if collection.split_path == [u'arte-latest']:
                    for video in self.browser.latest_videos():
                        yield video
                else:
                    for site in SITE.values:
                        if collection.split_path[0] == site.get('id') and collection.path_level in site.keys():
                            for item in getattr(self.browser, site.get(collection.path_level))():
                                yield item

            if collection.path_level >= 2:
                for site in SITE.values:
                    if collection.split_path[0] == site.get('id') and collection.path_level in site.keys():
                        for item in getattr(self.browser, site.get(collection.path_level))(collection.split_path):
                            yield item

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if BaseVideo in objs and (collection.split_path == [u'arte-latest'] or
                                  collection.split_path[0] in [value.get('id') for value in SITE.values]):
            return
        if BaseVideo in objs and collection.path_level >= 2 and\
                collection.split_path[0] in [value.get('id') for value in SITE.values]:
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {ArteVideo: fill_arte_video, ArteSiteVideo: fill_site_video}
