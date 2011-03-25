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
import lxml.html
import re

from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage
from weboob.tools.misc import to_unicode
from weboob.tools.parsers.lxmlparser import select, SelectElementException

from ..video import YoujizzVideo


__all__ = ['VideoPage']


class VideoPage(BasePage):

    def get_video(self, video=None):
        _id = to_unicode(self.group_dict['id'])
        if video is None:
            video = YoujizzVideo(_id)
        title_el = select(self.document.getroot(), 'title', 1)
        video.title = to_unicode(title_el.text.strip())

        # youjizz HTML is crap, we must parse it with regexps
        data = lxml.html.tostring(self.document.getroot())
        m = re.search(r'<strong>.*?Runtime.*?</strong> (.+?)<br.*>', data)
        if m:
            txt = m.group(1).strip()
            if txt == 'Unknown':
                video.duration = NotAvailable
            else:
                minutes, seconds = (int(v) for v in to_unicode(txt).split(':'))
                video.duration = datetime.timedelta(minutes=minutes, seconds=seconds)
        else:
            raise SelectElementException('Unable to retrieve video duration')

        video_file_urls = re.findall(r'"(http://media[^ ,]+\.flv)"', data)
        if len(video_file_urls) == 0:
            raise SelectElementException('Video URL not found')
        elif len(video_file_urls) > 1:
            raise SelectElementException('Many video file URL found')
        else:
            video.url = video_file_urls[0]

        return video

