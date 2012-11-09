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
from weboob.capabilities import NotAvailable
from weboob.tools.misc import html2text
from weboob.tools.browser import BasePage, BrokenPageError


from .video import DailymotionVideo


__all__ = ['IndexPage', 'VideoPage']


class IndexPage(BasePage):
    def iter_videos(self):
        for div in self.parser.select(self.document.getroot(), 'div.dmpi_video_item'):
            _id = div.attrib.get('data-id', None)

            if _id is None:
                self.browser.logger.warning('Unable to find the ID of a video')
                continue

            video = DailymotionVideo(_id)
            video.title = unicode(self.parser.select(div, 'h3 a', 1).text).strip()
            video.author = unicode(self.parser.select(div, 'div.dmpi_user_login', 1).find('a').find('span').text).strip()
            video.description = html2text(self.parser.tostring(self.parser.select(div, 'div.dmpi_video_description', 1))).strip() or unicode()
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
            url = unicode(self.parser.select(div, 'img.dmco_image', 1).attrib['data-src'])
            # remove the useless anti-caching
            url = re.sub('\?\d+', '', url)
            # use the bigger thumbnail
            url = url.replace('jpeg_preview_medium.jpg', 'jpeg_preview_large.jpg')
            video.thumbnail = Thumbnail(unicode(url))

            rating_div = self.parser.select(div, 'div.small_stars', 1)
            video.rating_max = self.get_rate(rating_div)
            video.rating = self.get_rate(rating_div.find('div'))

            video.set_empty_fields(NotAvailable, ('url',))
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

        video.title = unicode(self.parser.select(div, 'span.title', 1).text).strip()
        video.author = unicode(self.parser.select(div, 'a.name, span.name', 1).text).strip()
        try:
            video.description = html2text(self.parser.tostring(self.parser.select(div, 'div#video_description', 1))).strip() or unicode()
        except BrokenPageError:
            video.description = u''
        for script in self.parser.select(self.document.getroot(), 'div.dmco_html'):
            # TODO support videos from anyclip, cf http://www.dailymotion.com/video/xkyjiv for example
            if 'id' in script.attrib and script.attrib['id'].startswith('container_player_') and \
               script.find('script') is not None:
                text = script.find('script').text
                mobj = re.search(r'(?i)addVariable\(\"video\"\s*,\s*\"([^\"]*)\"\)', text)
                if mobj is None:
                    mobj = re.search('"sdURL":.*?"(.*?)"', urllib.unquote(text))
                    mediaURL = mobj.group(1).replace("\\", "")
                else:
                    mediaURL = urllib.unquote(mobj.group(1))
                video.url = mediaURL

        video.set_empty_fields(NotAvailable)

        return video
