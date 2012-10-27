# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon
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


from datetime import datetime
import re

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.tools.capabilities.thumbnail import Thumbnail
from weboob.capabilities.base import NotAvailable

from ..video import NolifeTVVideo


__all__ = ['IndexPage']


class IndexPage(BasePage):
    def iter_videos(self):
        for div in self.parser.select(self.document.getroot(), 'div.data_emissions ul li'):
            m = re.match('id-(\d+)', div.attrib.get('class', ''))
            if not m:
                continue

            img = self.parser.select(div, 'div.screenshot a img', 1)

            video = NolifeTVVideo(m.group(1))
            video.title = unicode(img.attrib['alt'])
            try:
                video.description = unicode(self.parser.select(div, 'div.tooltip div.border-bottom p, div.infos div.border-bottom p')[-1].text)
            except IndexError:
                video.description = NotAvailable

            video.thumbnail = Thumbnail(unicode(img.attrib['src']))
            try:
                dparts = self.parser.select(div, 'span.date_emission', 1).text.strip().split('/')
                hparts = self.parser.select(div, 'span.hour_emission', 1).text.strip().split('h')
                video.date = datetime(int(dparts[-1]), int(dparts[-2]), int(dparts[-3]),
                                      int(hparts[0]), int(hparts[1]))
            except (BrokenPageError,ValueError):
                video.date = NotAvailable

            video.set_empty_fields(NotAvailable, ('url',))

            yield video
