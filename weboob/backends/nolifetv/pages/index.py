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


from dateutil.parser import parse as parse_dt
import re

from weboob.tools.browser import BasePage
from weboob.tools.capabilities.thumbnail import Thumbnail
from weboob.capabilities.base import NotAvailable

from ..video import NolifeTVVideo


__all__ = ['IndexPage']


class IndexPage(BasePage):
    def iter_videos(self):
        div_list = self.parser.select(self.document.getroot(), 'div.ligne_video')
        for div in div_list:
            m = re.match('index.php\?id=(\d+)', div.find('a').attrib['href'])
            if not m:
                continue
            video = NolifeTVVideo(m.group(1))
            video.title = self.parser.select(div, 'span.span_title', 1).text
            video.description = self.parser.select(div, 'span.span_description', 1).text
            video.thumbnail = Thumbnail(self.parser.select(div, 'div.screen_video', 1).find('img').attrib['src'])
            try:
                video.date = parse_dt(self.parser.select(div, 'div.infos_video span.span_title', 1).text.strip())
            except Exception:
                video.date = NotAvailable

            rating_url = self.parser.select(div, 'span.description img')[0].attrib['src']
            m = re.match('.*view_level(\d+)\.gif', rating_url)
            if m:
                video.rating = int(m.group(1))
                video.rating_max = 21
            else:
                video.rating = video.rating_max = NotAvailable

            yield video
