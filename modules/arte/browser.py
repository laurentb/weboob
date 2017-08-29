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

from weboob.capabilities.collection import Collection
from weboob.capabilities.base import UserError
from weboob.capabilities import NotAvailable
from weboob.browser import PagesBrowser, URL
from weboob.tools.compat import quote, unicode

from .pages import VideosListPage, ArteJsonPage, SearchPage
from .video import VERSION_VIDEO, LANG, QUALITY, SITE, ArteEmptyVideo


__all__ = ['ArteBrowser']


class ArteBrowser(PagesBrowser):
    BASEURL = 'https://www.arte.tv/'

    search = URL('/guide/api/api/search/(?P<lang>\w{2})/(?P<pattern>[^/]+)/(?P<page>\d+)', SearchPage)

    webservice = URL('papi/tvguide/(?P<class_name>.*)/(?P<method_name>.*)/(?P<parameters>.*).json',
                     'http://(?P<__site>.*).arte.tv/(?P<_lang>\w{2})/player/(?P<_id>.*)',
                     'https://api.arte.tv/api/player/v1/config/(?P<__lang>\w{2})/(?P<vid>.*)\?vector=(?P<___site>.*)',
                     ArteJsonPage)
    videos_list = URL('http://(?P<site>.*).arte.tv/(?P<lang>\w{2})/?(?P<cat>.*?)',
                      'http://(?P<_site>.*).arte.tv/(?P<id>.+)',
                      VideosListPage)

    def __init__(self, lang, quality, order, format, version, *args, **kwargs):
        super(ArteBrowser, self).__init__(*args, **kwargs)
        self.order = order
        self.lang = next(value for key, value in LANG.items if key == lang)
        self.version = next(value for key, value in VERSION_VIDEO.items
                            if self.lang.get('label') in value.keys() and version == key)
        self.quality = next(value for key, value in QUALITY.items if key == quality)
        self.format = format

        if self.lang.get('label') not in self.version.keys():
            raise UserError('%s is not available for %s' % (self.lang.get('label'), version))

    def search_videos(self, pattern):
        return self.search.go(lang=self.lang['site'], pattern=quote(pattern), page='1').iter_videos()

        class_name = 'videos/plus7'
        method_name = 'search'
        parameters = '/'.join([self.lang.get('webservice'), 'L1', pattern, 'ALL', 'ALL', '-1',
                               self.order, '10', '0'])
        return self.webservice.go(class_name=class_name, method_name=method_name, parameters=parameters).iter_videos()

    def get_video(self, id, video=None):
        class_name = 'videos'
        method_name = 'stream/player'
        parameters = '/'.join([self.lang.get('webservice'), id, 'ALL', 'ALL'])
        video = self.webservice.go(class_name=class_name,
                                   method_name=method_name,
                                   parameters=parameters).get_video(obj=video)
        video.ext, video.url = self.get_url()
        return video

    def get_url(self):
        url, found_format = self.page.get_video_url(self.quality.get('label'), self.format,
                                                    self.version.get(self.lang.get('label')),
                                                    self.lang.get('version'))
        if found_format.startswith('HLS'):
            ext = u'm3u8'
            url = self.get_m3u8_link(url)
        else:
            ext = u'mp4'
            url = url
        return ext, url

    def get_m3u8_link(self, url):
        r = self.open(url).text.split('\n')
        baseurl = url.rpartition('/')[0]

        links_by_quality = []
        for line in r:
            if not line.startswith('#'):
                if baseurl not in line:
                    link = u'%s/%s' % (baseurl, line.replace('\n', ''))
                else:
                    link = unicode(line.replace('\n', ''))
                links_by_quality.append(link)

        if len(links_by_quality):
            try:
                return links_by_quality[self.quality.get('order')]
            except:
                return links_by_quality[0]
        return NotAvailable

    def get_video_from_program_id(self, _id):
        class_name = 'epg'
        method_name = 'program'
        parameters = '/'.join([self.lang.get('webservice'), 'L2', _id])
        video = self.webservice.go(class_name=class_name, method_name=method_name,
                                   parameters=parameters).get_program_video()
        if video:
            return self.get_video(video.id, video)
        else:
            video = self.webservice.go(__lang=self.lang.get('site'),
                                       vid=_id, ___site='ARTEPLUS7').get_program_video()
            video.ext, video.url = self.get_url()
            # buggy URLs
            video.url = video.url.replace('%255B', '%5B').replace('%255D', '%5D')
            return video

    def latest_videos(self):
        class_name = 'videos'
        method_name = 'plus7'
        parameters = '/'.join([self.lang.get('webservice'), 'L1', 'ALL', 'ALL', '-1', self.order, '10', '0'])
        return self.webservice.go(class_name=class_name, method_name=method_name, parameters=parameters).iter_videos()

    def get_arte_programs(self):
        class_name = 'epg'
        method_name = 'clusters'
        parameters = '/'.join([self.lang.get('webservice'), '0', 'ALL'])
        return self.webservice.go(class_name=class_name, method_name=method_name,
                                  parameters=parameters).iter_programs(title=self.lang.get('title'))

    def get_arte_program_videos(self, program):
        class_name = 'epg'
        method_name = 'cluster'
        parameters = '/'.join([self.lang.get('webservice'), program[-1]])
        available_videos = self.webservice.go(class_name=class_name, method_name=method_name,
                                              parameters=parameters).iter_program_videos()
        for item in available_videos:
            video = self.get_video_from_program_id(item.id)
            if video:
                yield video

    def get_arte_concert_categories(self):
        return self.videos_list.go(site=SITE.CONCERT.get('id'), lang=self.lang.get('site'),
                                   cat='').iter_arte_concert_categories()

    def get_arte_concert_videos(self, cat):
        return self.videos_list.go(site=SITE.CONCERT.get('id'), lang=self.lang.get('site'),
                                   cat='').iter_arte_concert_videos(cat=cat[-1])

    def get_arte_concert_video(self, id, video=None):
        json_url = self.videos_list.go(_site=SITE.CONCERT.get('id'), id=id).get_json_url()
        m = re.search('http://(?P<__site>.*).arte.tv/(?P<_lang>\w{2})/player/(?P<_id>.*)', json_url)
        if m:
            video = self.webservice.go(__site=m.group('__site'), _lang=m.group('_lang'),
                                       _id=m.group('_id')).get_arte_concert_video(obj=video)
            video.id = u'%s.%s' % (video._site, id)
            video.ext, video.url = self.get_url()
            return video

    def get_arte_cinema_categories(self, cat=[]):
        menu = self.videos_list.go(site=SITE.CINEMA.get('id'), lang=self.lang.get('site'),
                                   cat='').get_arte_cinema_menu()
        menuSplit = map(lambda x: x.split("/")[2:], menu)

        result = {}
        for record in menuSplit:
            here = result
            for item in record[:-1]:
                if item not in here:
                    here[item] = {}
                here = here[item]
            if "end" not in here:
                here["end"] = []
            here["end"].append(record[-1])

        cat = cat if not cat else cat[1:]

        if not cat and "end" in result:
            del result["end"]

        for el in cat:
            result = result.get(el)

        if "end" in result.keys():
            return self.page.iter_arte_cinema_categories(cat='/'.join(cat))
        else:
            categories = []
            for item in result.keys():
                if item == "programs":
                    continue
                categories.append(Collection([SITE.CINEMA.get('id'), unicode(item)], unicode(item)))
            return categories

    def get_arte_cinema_videos(self, cat):
        return self.videos_list.go(site=SITE.CINEMA.get('id'), lang=self.lang.get('site'),
                                   cat='/%s' % '/'.join(cat[1:])).get_arte_cinema_videos()

    def get_arte_cinema_video(self, id, video=None):
        json_url = self.videos_list.go(_site=SITE.CINEMA.get('id'), id=id).get_json_url()
        m = re.search('https://api.arte.tv/api/player/v1/config/(\w{2})/(.*)\?(vector|platform)=(.*)\&.*', json_url)
        if m:
            video = self.webservice.go(__lang=m.group(1),
                                       vid=m.group(2), ___site=m.group(4)).get_arte_cinema_video(obj=video)
            video.ext, video.url = self.get_url()
            video.id = id
            return video
        return ArteEmptyVideo()

    def get_arte_creative_categories(self):
        return self.videos_list.go(site=SITE.CREATIVE.get('id'), lang=self.lang.get('site'),
                                   cat='').iter_arte_creative_categories()

    def get_arte_creative_videos(self, cat):
        _cat = cat[-1].replace('^', '/') if cat[-1] != u'accueil' else ''
        return self.videos_list.go(site=SITE.CREATIVE.get('id'), lang=self.lang.get('site'),
                                   cat='/%s' % _cat).iter_arte_creative_videos(cat=cat[-1])

    def get_arte_creative_video(self, id, video=None):
        json_url = self.videos_list.go(_site=SITE.CREATIVE.get('id'), id=id).get_json_url()
        m = re.search('https://api.arte.tv/api/player/v1/config/(\w{2})/(.*)\?vector=(.*)\&.*', json_url)
        if m:
            video = self.webservice.go(__lang=m.group(1),
                                       vid=m.group(2), ___site=m.group(3)).get_arte_cinema_video(obj=video)
            video.ext, video.url = self.get_url()
            video.id = id
            return video
        return ArteEmptyVideo()

    def fetch_url(self, _id):
        self.webservice.go(__lang=self.lang['site'], vid=_id, ___site='ARTEPLUS7')
        return self.get_url()
