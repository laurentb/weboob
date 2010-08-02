# -*- coding: utf-8 -*-

# Copyright(C) 2010  Roger Philibert
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

from ..video import YoujizzVideo


__all__ = ['IndexPage']


class IndexPage(BasePage):
    def iter_videos(self):
        span_list = select(self.document.getroot(), 'span#miniatura')
        for span in span_list:
            a = select(span, 'a', 1)
            url = a.attrib['href']
            _id = re.sub(r'/videos/(.+)\.html', r'\1', url)

            thumbnail_url = span.find('.//img').attrib['src']

            title_el = select(span, 'span#title1', 1)
            title = title_el.text.strip()

            time_span = select(span, 'span.thumbtime span', 1)
            time_txt = time_span.text.strip()
            if time_txt == 'N/A':
                minutes, seconds = 0, 0
            elif ':' in time_txt:
                minutes, seconds = (int(v) for v in time_txt.split(':'))
            else:
                raise SelectElementException('Unable to parse the video duration: %s' % time_txt)


            yield YoujizzVideo(_id,
                               title=title,
                               duration=datetime.timedelta(minutes=minutes, seconds=seconds),
                               thumbnail_url=thumbnail_url,
                               )
