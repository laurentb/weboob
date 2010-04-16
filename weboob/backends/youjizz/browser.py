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

from logging import error
import re

from weboob.tools.browser import BaseBrowser

class YoujizzBrowser(BaseBrowser):
    video_file_regex = re.compile(r'"(http://media[^ ,]+\.flv)"')

    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()

    def get_video_title(self, page_url):
        raise NotImplementedError()

    def get_video_url(self, page_url):
        data = self.openurl(page_url).read()
        video_file_urls = re.findall(self.video_file_regex, data)
        if len(video_file_urls) == 0:
            return None
        else:
            if len(video_file_urls) > 1:
                error('Many video file URL found for given URL: %s' % video_file_urls)
            return video_file_urls[0]

