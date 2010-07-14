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
import datetime
from logging import warning

from weboob.tools.parsers.lxmlparser import select

from .base import PornPage
from ..video import YoupornVideo


class VideoPage(PornPage):
    def get_video(self, video=None):
        if not PornPage.on_loaded(self):
            return
        if video is None:
            video = YoupornVideo(self.group_dict['id'])
        video.title = self.get_title()
        video.url = self.get_url()
        self.set_details(video)
        return video

    def get_url(self):
        download_div = select(self.document.getroot(), '#download', 1)
        a = select(download_div, 'a', 1)
        return a.attrib['href']

    def get_title(self):
        element = select(self.document.getroot(), '#videoArea h1', 1)
        return unicode(element.getchildren()[0].tail).strip()

    DATE_REGEXP = re.compile("\w+ (\w+) (\d+) (\d+):(\d+):(\d+) (\d+)")
    MONTH2I = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def set_details(self, v):
        details_div = select(self.document.getroot(), '#details', 1)
        for li in details_div.getiterator('li'):
            span = li.find('span')
            name = span.text.strip()
            value = span.tail.strip()

            if name == 'Duration:':
                seconds = minutes = 0
                for word in value.split():
                    if word.endswith('min'):
                        minutes = int(word[:word.find('min')])
                    elif word.endswith('sec'):
                        seconds = int(word[:word.find('sec')])
                v.duration = datetime.timedelta(minutes=minutes, seconds=seconds)
            elif name == 'Submitted:':
                author = li.find('i')
                if author is None:
                    author = li.find('a')
                if author is None:
                    v.author = value
                else:
                    v.author = author.text
            elif name == 'Rating:':
                r = value.split()
                v.rating = float(r[0])
                v.rating_max = float(r[2])
            elif name == 'Date:':
                m = self.DATE_REGEXP.match(value)
                if m:
                    month = self.MONTH2I.index(m.group(1))
                    day = int(m.group(2))
                    hour = int(m.group(3))
                    minute = int(m.group(4))
                    second = int(m.group(5))
                    year = int(m.group(6))
                    v.date = datetime.datetime(year, month, day, hour, minute, second)
