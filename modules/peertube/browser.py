# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from __future__ import unicode_literals

from weboob.browser.browsers import APIBrowser
from weboob.capabilities.video import BaseVideo
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.file import LICENSES


class PeertubeBrowser(APIBrowser):
    # source: server/initializers/constants.ts
    SITE_LICENSES = {
        1: LICENSES.CCBY,
        2: LICENSES.CCBYSA,
        3: LICENSES.CCBYND,
        4: LICENSES.CCBYNC,
        5: LICENSES.CCBYNCSA,
        6: LICENSES.CCBYNCND,
        7: LICENSES.PD,
    }

    def __init__(self, baseurl, *args, **kwargs):
        super(PeertubeBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = baseurl

    def search_videos(self, pattern, sortby):
        j = self.request('/api/v1/search/videos?count=10&sort=-match', params={
            'search': pattern,
            'start': 0,
        })

        for item in j['data']:
            video = BaseVideo()
            self._parse_video(video, item)
            yield video

    def get_video(self, id, video=None):
        item = self.request('/api/v1/videos/%s' % id)

        if not video:
            video = BaseVideo()

        self._parse_video(video, item)

        video._torrent = item['files'][0]['magnetUri']
        video.url = item['files'][0]['fileUrl']
        video.ext = video.url.rsplit('.', 1)[-1]
        video.size = item['files'][0]['size']

        return video

    def _parse_video(self, video, item):
        video.id = item['uuid']
        video.nsfw = item['nsfw']
        video.title = item['name']
        video.description = item['description']
        video.author = item['account']['name']
        video.duration = item['duration']
        video.license = self.SITE_LICENSES[item['licence']['id']]
        video.thumbnail = Thumbnail(self.absurl(item['thumbnailPath']))
