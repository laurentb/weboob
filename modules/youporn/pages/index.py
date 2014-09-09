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

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import BaseImage

from .base import PornPage
from ..video import YoupornVideo


class IndexPage(PornPage):
    def iter_videos(self):
        for li in self.document.getroot().xpath('//ul/li[@class="videoBox"]'):
            a = li.find('div').find('a')
            if a is None or a.find('img') is None:
                continue

            thumbnail_url = a.find('img').attrib['src']

            a = self.parser.select(li, './/a[@class="videoTitle"]', 1, 'xpath')

            url = a.attrib['href']
            _id = url[len('/watch/'):]
            _id = _id[:_id.find('/')]

            video = YoupornVideo(int(_id))
            video.title = unicode(a.text.strip())
            video.thumbnail = BaseImage(thumbnail_url)
            video.thumbnail.url = video.thumbnail.id

            hours = minutes = seconds = 0
            div = li.cssselect('div.duration')
            if len(div) > 0:
                pack = [int(s) for s in div[0].text.strip().split(':')]
                if len(pack) == 3:
                    hours, minutes, seconds = pack
                elif len(pack) == 2:
                    minutes, seconds = pack

            video.duration = datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)

            div = li.cssselect('div.rating')
            if div:
                video.rating = int(div[0].text.strip('% '))
                video.rating_max = 100

            video.set_empty_fields(NotAvailable, ('url', 'author'))

            yield video
