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

from weboob.tools.browser import Browser

from .pages.index import IndexPage
from .pages.video import VideoPage

class YoupornBrowser(Browser):
    DOMAIN = 'youporn.com'
    PROTOCOL = 'http'
    PAGES = {'http://[w\.]*youporn\.com/?': IndexPage,
             'http://[w\.]*youporn\.com/watch/.+': VideoPage,
            }

    def __init__(self):
        # Disallow arguments
        Browser.__init__(self)

    def get_video_title(self, page_url):
        self.location(page_url)
        return self.page.title

    def get_video_url(self, page_url):
        self.location(page_url)
        return self.page.url
