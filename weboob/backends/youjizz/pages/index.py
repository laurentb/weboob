# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Roger Philibert

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

import re

from weboob.capabilities.video import Video
from weboob.tools.browser import BasePage


__all__ = ['IndexPage']


class IndexPage(BasePage):
    def iter_videos(self):
        span_list = self.document.getroot().cssselect("span#miniatura")
        if not span_list:
            return

        for span in span_list:
            a = span.find('.//a')
            if a is None:
                continue
            url = a.attrib['href']
            _id = re.sub(r'/videos/(.+)\.html', r'\1', url)

            preview_url = span.find('.//img').attrib['src']

            title1 = span.cssselect('span#title1')
            if title1 is None:
                title = None
            else:
                title = title1[0].text.strip()

            duration = 0
            thumbtime = span.cssselect('span.thumbtime')
            if thumbtime is not None:
                time_span = thumbtime[0].find('span')
                minutes, seconds = time_span.text.strip().split(':')
                duration = 60 * int(minutes) + int(seconds)

            yield Video(_id,
                        title=title,
                        page_url=self.browser.id2url(_id),
                        duration=duration,
                        preview_url=preview_url,
                        nsfw=True)
