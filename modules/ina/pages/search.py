# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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

from ..video import InaVideo


__all__ = ['SearchPage']


class SearchPage(BasePage):
    URL_REGEXP = re.compile(r'/(.+)/(.+)\.jpeg')

    def iter_videos(self):
        try:
            ul = self.parser.select(self.document.getroot(), 'div.container-videos ul', 1)
        except BrokenPageError:
            # It means there are no results.
            return
        for li in ul.findall('li'):
            url =  li.find('a').find('img').attrib['src']

            id = re.sub(self.URL_REGEXP, r'\2', url)
            video = InaVideo(id)

            video.thumbnail = BaseImage(u'http://boutique.ina.fr%s' % url)
            video.thumbnail.url = video.thumbnail.id

            # The title is poorly encoded is the source, we have to encode/decode it again
            video.title = unicode(self.parser.select(li, 'p.titre', 1).text).encode('raw_unicode_escape').decode('utf8')

            date = self.parser.select(li, 'p.date', 1).text
            day, month, year = [int(s) for s in date.split('/')]
            video.date = datetime.datetime(year, month, day)

            duration = self.parser.select(li, 'p.duree', 1).text
            m = re.match(r'((\d+)h)?((\d+)min)?(\d+)s', duration)
            if m:
                video.duration = datetime.timedelta(hours=int(m.group(2) or 0), minutes=int(m.group(4) or 0), seconds=int(m.group(5)))
            else:
                raise BrokenPageError('Unable to match duration (%r)' % duration)

            yield video
