# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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

import datetime
import urllib
import re

from weboob.tools.capabilities.thumbnail import Thumbnail
from weboob.capabilities.base import NotAvailable
from weboob.tools.misc import html2text
from weboob.tools.browser import BasePage, BrokenPageError


from .video import DailymotionVideo


__all__ = ['IndexPage', 'VideoPage']


class IndexPage(BasePage):
    def iter_videos(self):
        for div in self.parser.select(self.document.getroot(), 'div.dmpi_video_item'):
            _id = 0
            for cls in div.attrib['class'].split():
                if cls.startswith('id_'):
                    _id = int(cls[3:])
                    break

            if _id == 0:
                self.browser.logger.warning('Unable to find the ID of a video')
                continue

            video = DailymotionVideo(int(_id))
            video.title = self.parser.select(div, 'h3 a', 1).text
            video.author = self.parser.select(div, 'div.dmpi_user_login', 1).find('a').text
            video.description = html2text(self.parser.tostring(self.parser.select(div, 'div.dmpi_video_description', 1))).strip()
            try:
                parts = self.parser.select(div, 'div.duration', 1).text.split(':')
            except BrokenPageError:
                # it's probably a live, np.
                video.duration = NotAvailable
            else:
                if len(parts) == 1:
                    seconds = parts[0]
                    hours = minutes = 0
                elif len(parts) == 2:
                    minutes, seconds = parts
                    hours = 0
                elif len(parts) == 3:
                    hours, minutes, seconds = parts
                else:
                    raise BrokenPageError('Unable to parse duration %r' % self.parser.select(div, 'div.duration', 1).text)
                video.duration = datetime.timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))
            url = self.parser.select(div, 'img.dmco_image', 1).attrib['src']
            video.thumbnail = Thumbnail(url)

            rating_div = self.parser.select(div, 'div.small_stars', 1)
            video.rating_max = self.get_rate(rating_div)
            video.rating = self.get_rate(rating_div.find('div'))
            # XXX missing date
            video.date = NotAvailable
            yield video

    def get_rate(self, div):
        m = re.match('width: *(\d+)px', div.attrib['style'])
        if m:
            return int(m.group(1))
        else:
            self.browser.logger.warning('Unable to parse rating: %s' % div.attrib['style'])
            return 0

class VideoPage(BasePage):
    def get_video(self, video=None):
        if video is None:
            video = DailymotionVideo(self.group_dict['id'])

        div = self.parser.select(self.document.getroot(), 'div#content', 1)

        video.title = self.parser.select(div, 'span.title', 1).text
        video.author = self.parser.select(div, 'a.name', 1).text
        video.description = self.parser.select(div, 'div#video_description', 1).text
        for script in self.parser.select(self.document.getroot(), 'div.dmco_html'):
            if 'id' in script.attrib and script.attrib['id'].startswith('container_player_'):
                text = script.find('script').text
                mobj = re.search(r'(?i)addVariable\(\"video\"\s*,\s*\"([^\"]*)\"\)', text)
                if mobj is None:
                    mobj = re.search('"sdURL":.*?"(.*?)"', urllib.unquote(text))
                    mediaURL = mobj.group(1).replace("\\", "")
                else:
                    mediaURL = urllib.unquote(mobj.group(1))
                video.url = mediaURL

        return video
