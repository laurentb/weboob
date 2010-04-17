# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

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

from weboob.tools.browser import BasePage
from weboob.capabilities.video import Video

class ResultsPage(BasePage):
    WATCH_RE = re.compile('/watch?v=(\w+)')
    def iter_videos(self):
        for div in self.document.getroot().cssselect("div[class^=video-entry]"):
            a = div.find('a')
            if a is None:
                print 'wtf'
                continue

            _id = ''
            m = self.WATCH_RE.match(a.attrib['href'])
            if m:
                _id = m.group(1)

            title = a.find('span').find('img').attrib['alt']
            preview_url = a.find('span').find('img').attrib['src']
            if preview_url.endswith('.gif'):
                preview_url = a.find('span').find('img').attrib['thumb']

            vtime = a.find('span').find('span')
            duration = 0
            if not vtime is None:
                vtime = vtime.find('span').text.split(':')
                if len(vtime) > 0:
                    duration += int(vtime[-1])
                if len(vtime) > 1:
                    duration += 60 * int(vtime[-2])
                if len(vtime) > 3:
                    duration += 3600 * int(vtime[-3])
                if len(vtime) > 4:
                    print 'WTF'

            author = ''
            author_div = div.cssselect('span[class=video-username]')
            if author_div:
                author = author_div[0].find('a').text.strip()
            yield Video(_id,
                        title,
                        author=author,
                        duration=duration,
                        preview_url=preview_url)
