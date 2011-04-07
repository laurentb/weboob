# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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

from .base import PornPage
from ..video import YoupornVideo


__all__ = ['IndexPage']


class IndexPage(PornPage):
    def iter_videos(self):
        uls = self.document.getroot().cssselect("ul[class=clearfix]")
        if not uls:
            return

        for ul in uls:
            for li in ul.findall('li'):
                a = li.find('a')
                if a is None or a.find('img') is None:
                    continue

                thumbnail_url = a.find('img').attrib['src']

                h1 = li.find('h1')
                a = h1.find('a')
                if a is None:
                    continue

                url = a.attrib['href']
                _id = url[len('/watch/'):]
                _id = _id[:_id.find('/')]
                title = a.text.strip()

                minutes = seconds = 0
                div = li.cssselect('div[class=duration_views]')
                if div:
                    h2 = div[0].find('h2')
                    minutes = int(h2.text.strip())
                    seconds = int(h2.find('span').tail.strip())

                rating = 0
                rating_max = 0
                div = li.cssselect('div[class=rating]')
                if div:
                    p = div[0].find('p')
                    rating = float(p.text.strip())
                    rating_max = float(p.find('span').text.strip()[2:])

                yield YoupornVideo(int(_id),
                                   title=title,
                                   rating=rating,
                                   rating_max=rating_max,
                                   duration=datetime.timedelta(minutes=minutes, seconds=seconds),
                                   thumbnail_url=thumbnail_url,
                                   )
