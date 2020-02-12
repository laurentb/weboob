# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


import re
from collections import OrderedDict

from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.capabilities.collection import CapCollection, CollectionNotFound, Collection
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value

from .browser import ArteBrowser
from .video import VERSION_VIDEO, FORMATS, LANG, QUALITY, SITE, get_site_enum_by_id


__all__ = ['ArteModule']


class ArteModule(Module, CapVideo, CapCollection):
    NAME = 'arte'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    VERSION = '2.1'
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
        m = re.match('https?://www.arte.tv/\w+/videos/(?P<id>.+)/(.*)', _id)
        if m:
            return m.group(1)

        if not _id.startswith('http'):
            return _id

        return None

    def get_video(self, _id, video=None):
        _id = self.parse_id(_id)

        if _id is None:
            return None

        return self.browser.get_video(_id, video)

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        return self.browser.search_videos(pattern)

    def fill_arte_video(self, video, fields):
        if fields != ['thumbnail']:
            video = self.browser.get_video(video.id, video)

        if 'thumbnail' in fields and video and video.thumbnail:
            video.thumbnail.data = self.browser.open(video.thumbnail.url).content
        return video

    def iter_resources(self, objs, split_path):
        collection = self.get_collection(objs, split_path)

        if BaseVideo in objs:
            if collection.path_level == 0:
                return [Collection([site.get('id')], site.get('label')) for site in SITE.values]

            elif len(split_path) == 1:
                site = get_site_enum_by_id(split_path[0])
                subsite = site.get('enum', None)

                if site == SITE.PROGRAM:
                    return self.browser.get_arte_programs(split_path)
                elif site == SITE.GUIDE:
                    return self.browser.get_arte_guide_days(split_path)
                elif site == SITE.CREATIVE:
                    return self.browser.get_arte_creative_videos()
                elif subsite:
                    return self.browser.get_arte_generic_subsites(split_path, subsite)

            elif collection.path_level > 1:
                site = get_site_enum_by_id(split_path[0])

                if site == SITE.GUIDE:
                    return self.browser.get_arte_guide_videos(split_path)
                else:
                    subsite = site.get('enum', {})
                    if subsite:
                        subsite = dict(subsite.items)

                    return self.browser.get_arte_navigation(split_path,
                                                            subsite.get('COLLECTION', {}).get('id', r''),
                                                            subsite.get('PLAYLIST', {}).get('id', r''),
                                                            subsite.get('MAGAZINE', {}).get('id', r''))

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if BaseVideo in objs and (collection.split_path[0] in [value.get('id') for value in SITE.values]):
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {BaseVideo: fill_arte_video}
