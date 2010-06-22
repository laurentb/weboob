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

from .base import PornPage
from ..video import YoupornVideo

class VideoPage(PornPage):
    URL_REGEXP = re.compile("https?://[w\.]*youporn.com/watch/(\d+)/?.*")

    def on_loaded(self):
        if not PornPage.on_loaded(self):
            return

        self.video = YoupornVideo(self.get_id(),
                                  self.get_title(),
                                  self.get_url(),
                                  nsfw=True)

        self.set_details(self.video)

    def get_id(self):
        m = self.URL_REGEXP.match(self.url)
        if m:
            return int(m.group(1))
        warning("Unable to parse ID")
        return 0

    def get_url(self):
        el = self.document.getroot().cssselect('div[id=download]')
        if el:
            return el[0].cssselect('a')[0].attrib['href']

    def get_title(self):
        el = self.document.getroot().cssselect('h1')
        if el:
            return unicode(el[0].getchildren()[0].tail).strip()

    DATE_REGEXP = re.compile("\w+ (\w+) (\d+) (\d+):(\d+):(\d+) (\d+)")
    MONTH2I = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def set_details(self, v):
        div = self.document.getroot().cssselect('div[id=details]')
        if not div:
            return

        for li in div[0].getiterator('li'):
            span = li.find('span')
            name = span.text.strip()
            value = span.tail.strip()

            if name == 'Duration:':
                duration = 0
                for word in value.split():
                    if word.endswith('min'):
                        duration += 60 * int(word[:word.find('min')])
                    elif word.endswith('sec'):
                        duration += int(word[:word.find('sec')])
                v.duration = duration
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
