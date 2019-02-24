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

import re

from weboob.browser import PagesBrowser, URL
from weboob.tools.compat import quote_plus
from .pages import IndexPage, VideoPage


__all__ = ['DailymotionBrowser']


class DailymotionBrowser(PagesBrowser):
    BASEURL = 'http://www.dailymotion.com'

    video_page = URL(r'http://[w\.]*dailymotion\.com/video/(?P<_id>.*)',
                     VideoPage)

    latest_page = URL(r'/1', IndexPage)
    index_page = URL(r'http://[w\.]*dailymotion\.com/(?P<search>.*)',
                     r'http://[w\.]*dailymotion\.com/1',
                     r'http://[w\.]*dailymotion\.com/[a-z\-]{2,5}/1',
                     r'http://[w\.]*dailymotion\.com/[a-z\-]{2,5}/(\w+/)?search/.*',
                     IndexPage)

    def __init__(self, resolution, format, *args, **kwargs):
        self.resolution = resolution
        self.format = format
        PagesBrowser.__init__(self, *args, **kwargs)

    def get_video(self, _id, video=None):
        video = self.video_page.go(_id=_id).get_video(obj=video)

        if video._formats and self.format in video._formats:
            video.ext = self.format
            if self.format == u'm3u8':
                video.url = self.retrieve_m3u8_url(video._formats.get(self.format))
            elif self.resolution in video._formats.get(self.format):
                video.url = video._formats.get(self.format).get(self.resolution)
            else:
                video.url = video._formats.get(self.format).values()[-1]
        return video

    def retrieve_m3u8_url(self, urls):
        if self.resolution in urls:
            return urls.get(self.resolution)

        return_next = False
        for resolution, url in urls.items():
            for item in self.read_url(url):
                if return_next:
                    return unicode(item.split('#')[0])

                m = re.match('^#.*,NAME="%s"' % self.resolution, item)
                if not m:
                    continue

                return_next = True
        return unicode(item.split('#')[0])

    def read_url(self, url):
        r = self.open(url, stream=True)
        buf = r.iter_lines()
        return buf

    def search_videos(self, pattern, sortby):
        pattern = pattern.replace('/', '').encode('utf-8')
        if sortby is None:
            url = 'en/search/%s/1' % quote_plus(pattern)
        else:
            url = 'en/%s/search/%s/1' % (sortby, quote_plus(pattern))

        return self.index_page.go(search=url).iter_videos()

    def latest_videos(self):
        return self.latest_page.go().iter_videos()
