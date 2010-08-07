# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import re

from weboob.tools.browser import BasePage
from weboob.tools.parsers.lxmlparser import select

from .video import ArteVideo


__all__ = ['IndexPage', 'VideoPage']


class IndexPage(BasePage):
    def iter_videos(self):
        videos = self.document.getroot().cssselect("div[class=video]")
        for div in videos:
            title = div.find('h2').find('a').text
            m = re.match(r'/fr/videos/(.*)\.html', div.find('h2').find('a').attrib['href'])
            _id = ''
            if m:
                _id = m.group(1)
            rating = rating_max = 0
            rates = select(div, 'div[class=rateContainer]', 1)
            for r in rates.findall('div'):
                if 'star-rating-on' in r.attrib['class']:
                    rating += 1
                rating_max += 1

            thumb = select(div, 'img[class=thumbnail]', 1)
            thumbnail_url = 'http://videos.arte.tv' + thumb.attrib['src']

            yield ArteVideo(_id,
                            title=title,
                            rating=rating,
                            rating_max=rating_max,
                            thumbnail_url=thumbnail_url)

class VideoPage(BasePage):
    VIDEO_SIGNATURE_REGEX = re.compile(r'&t=([^ ,&]*)')

    def get_video(self, video=None):
        return video
