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


import datetime
import re

from weboob.tools.browser import BasePage
from weboob.tools.parsers.lxmlparser import select, SelectElementException

from ..video import InaVideo


__all__ = ['SearchPage']


class SearchPage(BasePage):
    URL_REGEXP = re.compile('/video/(.+).html')

    def iter_videos(self):
        ul = select(self.document.getroot(), 'div.container-videos ul', 1)
        for li in ul.findall('li'):
            id = re.sub(r'/video/(.+)\.html', r'\1', li.find('a').attrib['href'])

            thumbnail = 'http://boutique.ina.fr%s' % li.find('a').find('img').attrib['src']

            title = select(li, 'p.titre', 1).text

            date = select(li, 'p.date', 1).text
            day, month, year = [int(s) for s in date.split('/')]
            date = datetime.datetime(year, month, day)

            duration = select(li, 'p.duree', 1).text
            m = re.match(r'((\d+)h)?((\d+)min)?(\d+)s', duration)
            if m:
                duration = datetime.timedelta(hours=int(m.group(2) or 0), minutes=int(m.group(4) or 0), seconds=int(m.group(5)))
            else:
                raise SelectElementException('Unable to match duration (%r)' % duration)

            yield InaVideo(id,
                           title=title,
                           date=date,
                           duration=duration,
                           thumbnail_url=thumbnail,
                          )
