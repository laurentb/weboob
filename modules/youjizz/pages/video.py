# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Roger Philibert
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
import lxml.html
import re

from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage, BrokenPageError
from weboob.tools.misc import to_unicode

from ..video import YoujizzVideo


__all__ = ['VideoPage']


class VideoPage(BasePage):
    def get_video(self, video=None):
        _id = to_unicode(self.group_dict['id'])
        if video is None:
            video = YoujizzVideo(_id)
        title_el = self.parser.select(self.document.getroot(), 'title', 1)
        video.title = to_unicode(title_el.text.strip())

        # youjizz HTML is crap, we must parse it with regexps
        data = lxml.html.tostring(self.document.getroot())
        m = re.search(r'<strong>.*?Runtime.*?</strong> (.+?)</div>', data)
        if m:
            txt = m.group(1).strip()
            if txt == 'Unknown':
                video.duration = NotAvailable
            else:
                minutes, seconds = (int(v) for v in to_unicode(txt).split(':'))
                video.duration = datetime.timedelta(minutes=minutes, seconds=seconds)
        else:
            raise BrokenPageError('Unable to retrieve video duration')

        real_id = int(_id.split('-')[-1])
        data = self.browser.readurl('http://www.youjizz.com/videos/embed/%s' % real_id)

        video_file_urls = re.findall(r'"(http://[^",]+\.youjizz\.com[^",]+\.flv(?:\?[^"]*)?)"', data)
        if len(video_file_urls) == 0:
            raise BrokenPageError('Video URL not found')
        elif len(video_file_urls) > 1:
            raise BrokenPageError('Many video file URL found')
        else:
            video.url = to_unicode(video_file_urls[0])

        return video
