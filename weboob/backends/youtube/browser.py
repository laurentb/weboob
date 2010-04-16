# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz

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

from weboob.tools.browser import BaseBrowser
from weboob.tools.parsers.lxmlparser import LxmlHtmlParser

from .pages import VideoPage

__all__ = ['YoutubeBrowser']

class YoutubeBrowser(BaseBrowser):
    video_signature_regex = re.compile(r'&t=([^ ,&]*)')

    def __init__(self, *args, **kwargs):
        kwargs['parser'] = LxmlHtmlParser()
        self.PAGES = {r'.*youtube\.com/watch\?v=(.+)': VideoPage}
        BaseBrowser.__init__(self, *args, **kwargs)

    def get_video_title(self, page_url):
        self.location(page_url)
        return self.page.title

    def get_video_url(self, page_url):
        def find_video_signature(data):
            for video_signature in re.finditer(self.video_signature_regex, data):
                return video_signature.group(1)
            return None
        data = self.openurl(page_url).read()
        video_signature = find_video_signature(data)
        m = re.match(r'.*youtube\.com/watch\?v=(.+)', page_url)
        if m:
            video_id = m.group(1)
            url = 'http://www.youtube.com/get_video?video_id=%s&t=%s&fmt=18' % (video_id, video_signature)
            return url
        else:
            return None
