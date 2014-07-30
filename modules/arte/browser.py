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
import datetime
import time
import urllib

from weboob.capabilities import NotAvailable
from weboob.capabilities.image import BaseImage
from weboob.tools.json import json as simplejson
from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url

from .pages import ArteLivePage, ArteLiveVideoPage
from .video import ArteVideo, ArteLiveVideo

__all__ = ['ArteBrowser']


class ArteBrowser(BaseBrowser):
    DOMAIN = u'videos.arte.tv'
    ENCODING = None
    PAGES = {r'http://concert.arte.tv/\w+': ArteLivePage,
             r'http://concert.arte.tv/(?P<id>.+)': ArteLiveVideoPage,
            }

    LIVE_LANG = {'F': 'fr',
                 'D': 'de'
                 }

    API_URL = 'http://arte.tv/papi/tvguide'

    def __init__(self, lang, quality, order, *args, **kwargs):
        self.lang = lang
        self.quality = quality
        self.order = order
        BaseBrowser.__init__(self, *args, **kwargs)

    @id2url(ArteVideo.id2url)
    def get_video(self, url, video=None):
        response = self.openurl('%s/ALL.json' % url)
        result = simplejson.loads(response.read(), self.ENCODING)

        if video is None:
            video = self.create_video(result['video'])
        try:
            video.url = self.get_m3u8_link(result['video']['VSR'][0]['VUR'])
            video.ext = u'm3u8'
        except:
            video.url, video.ext = NotAvailable, NotAvailable

        return video

    def get_m3u8_link(self, url):
        r = self.openurl(url)
        baseurl = url.rpartition('/')[0]

        links_by_quality = []
        for line in r.readlines():
            if not line.startswith('#'):
                links_by_quality.append(u'%s/%s' % (baseurl, line.replace('\n', '')))

        if len(links_by_quality):
            try:
                return links_by_quality[self.quality[1]]
            except:
                return links_by_quality[0]
        return NotAvailable

    @id2url(ArteLiveVideo.id2url)
    def get_live_video(self, url, video=None):
        self.location(url)
        assert self.is_on_page(ArteLiveVideoPage)
        json_url, video = self.page.get_video(video)
        return self.fill_live_video(video, json_url)

    def fill_live_video(self, video, json_url):
        response = self.openurl(json_url)
        result = simplejson.loads(response.read(), self.ENCODING)

        quality = None
        if 'VSR' in result['videoJsonPlayer']:
            for item in result['videoJsonPlayer']['VSR']:
                if self.quality[0] in item:
                    quality = item
                    break

            if not quality:
                url = result['videoJsonPlayer']['VSR'][0]['url']
                ext = result['videoJsonPlayer']['VSR'][0]['mediaType']
            else:
                url = result['videoJsonPlayer']['VSR'][quality]['url']
                ext = result['videoJsonPlayer']['VSR'][quality]['mediaType']

            video.url = u'%s' % url
            video.ext = u'%s' % ext
            if 'VDA' in result['videoJsonPlayer']:
                date_string = result['videoJsonPlayer']['VDA'][:-6]

                try:
                    video.date = datetime.datetime.strptime(date_string, '%d/%m/%Y %H:%M:%S')
                except TypeError:
                    video.date = datetime.datetime(*(time.strptime(date_string, '%d/%m/%Y %H:%M:%S')[0:6]))

            if 'VDU' in result['videoJsonPlayer'].keys():
                video.duration = int(result['videoJsonPlayer']['VDU'])

            if 'IUR' in result['videoJsonPlayer']['VTU'].keys():
                video.thumbnail = BaseImage(result['videoJsonPlayer']['VTU']['IUR'])
                video.thumbnail.url = video.thumbnail.id
        return video

    def home(self):
        self.location('http://videos.arte.tv/%s/videos/toutesLesVideos' % self.lang)

    def get_video_from_program_id(self, _id):
        class_name = 'epg'
        method_name = 'program'
        level = 'L2'
        url = self.API_URL \
            + '/' + class_name \
            + '/' + method_name \
            + '/' + self.lang \
            + '/' + level \
            + '/' + _id \
            + '.json'

        response = self.openurl(url)
        result = simplejson.loads(response.read(), self.ENCODING)
        video = self.create_video(result['abstractProgram']['VDO'])
        return self.get_video(video.id, video)

    def search_videos(self, pattern):
        class_name = 'videos/plus7'
        method_name = 'search'
        level = 'L1'
        cluster = 'ALL'
        channel = 'ALL'
        limit = '10'
        offset = '0'

        url = self.create_url_plus7(class_name, method_name, level, cluster, channel, limit, offset, pattern)
        response = self.openurl(url)
        result = simplejson.loads(response.read(), self.ENCODING)
        return self.create_video_from_plus7(result['videoList'])

    def create_video_from_plus7(self, result):
        for item in result:
            yield self.create_video(item)

    def create_video(self, item):
        video = ArteVideo(item['VID'])
        if 'VSU' in item:
            video.title = u'%s : %s' % (item['VTI'], item['VSU'])
        else:
            video.title = u'%s' % (item['VTI'])
        video.rating = int(item['VRT'])

        if 'programImage' in item:
            url = u'%s' % item['programImage']
            video.thumbnail = BaseImage(url)
            video.thumbnail.url=video.thumbnail.id

        video.duration = datetime.timedelta(seconds=int(item['videoDurationSeconds']))
        video.set_empty_fields(NotAvailable, ('url',))
        if 'VDE' in item:
            video.description = u'%s' % item['VDE']
        if 'VDA' in item:
            m = re.match('(\d{2})\s(\d{2})\s(\d{4})(.*?)', item['VDA'])
            if m:
                dd = int(m.group(1))
                mm = int(m.group(2))
                yyyy = int(m.group(3))
                video.date = datetime.date(yyyy, mm, dd)
        return video

    def create_url_plus7(self, class_name, method_name, level, cluster, channel, limit, offset, pattern=None):
        url = self.API_URL \
            + '/' + class_name \
            + '/' + method_name \
            + '/' + self.lang \
            + '/' + level

        if pattern:
            url += '/' + urllib.quote(pattern.encode('utf-8'))

        url += '/' + channel \
            + '/' + cluster \
            + '/' + '-1' \
            + '/' + self.order \
            + '/' + limit \
            + '/' + offset \
            + '.json'

        return url

    def latest_videos(self):
        class_name = 'videos'
        method_name = 'plus7'
        level = 'L1'
        cluster = 'ALL'
        channel = 'ALL'
        limit = '10'
        offset = '0'

        url = self.create_url_plus7(class_name, method_name, level, cluster, channel, limit, offset)
        response = self.openurl(url)
        result = simplejson.loads(response.read(), self.ENCODING)
        return self.create_video_from_plus7(result['videoList'])

    def get_arte_live_categories(self):
        self.location('http://concert.arte.tv/%s' % self.LIVE_LANG[self.lang])
        assert self.is_on_page(ArteLivePage)
        return self.page.iter_resources()

    def live_videos(self, cat):
        self.location('http://concert.arte.tv/%s' % self.LIVE_LANG[self.lang])
        assert self.is_on_page(ArteLivePage)
        return self.page.iter_videos(cat, lang=self.LIVE_LANG[self.lang])
