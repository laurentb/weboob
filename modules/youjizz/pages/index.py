# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Roger Philibert
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
import re

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.capabilities.image import BaseImage
from weboob.tools.misc import to_unicode

from ..video import YoujizzVideo


__all__ = ['IndexPage']


class IndexPage(BasePage):
    def iter_videos(self):
        span_list = self.parser.select(self.document.getroot(), 'span#miniatura')
        for span in span_list:
            a = self.parser.select(span, 'a', 1)
            url = a.attrib['href']
            _id = re.sub(r'/videos/(.+)\.html', r'\1', url)

            video = YoujizzVideo(_id)

            video.thumbnail = BaseImage(span.find('.//img').attrib['data-original'])
            video.thumbnail.url = video.thumbnail.id

            title_el = self.parser.select(span, 'span#title1', 1)
            video.title = to_unicode(title_el.text.strip())

            time_span = self.parser.select(span, 'span.thumbtime span', 1)
            time_txt = time_span.text.strip().replace(';', ':')
            hours, minutes, seconds = 0, 0, 0
            if ':' in time_txt:
                t = time_txt.split(':')
                t.reverse()
                seconds = int(t[0])
                minutes = int(t[1])
                if len(t) == 3:
                    hours = int(t[2])
            elif time_txt != 'N/A':
                raise BrokenPageError('Unable to parse the video duration: %s' % time_txt)

            video.duration = datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

            yield video
