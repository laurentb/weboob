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
import urllib

from weboob.tools.browser import Browser

from .pages.index import IndexPage
from .pages.video import VideoPage

class YoupornBrowser(Browser):
    DOMAIN = 'youporn.com'
    PROTOCOL = 'http'
    PAGES = {'http://[w\.]*youporn\.com/?': IndexPage,
             'http://[w\.]*youporn\.com/search.*': IndexPage,
             'http://[w\.]*youporn\.com/watch/.+': VideoPage,
            }

    def __init__(self):
        # Disallow arguments
        Browser.__init__(self)

    def id2url(self, _id):
        if isinstance(_id, int) or isinstance(_id, (str,unicode)) and _id.isdigit():
            return 'http://www.youporn.com/watch/%d' % int(_id)
        else:
            return str(_id)

    def iter_search_results(self, pattern):
        if not pattern:
            self.home()
        else:
            self.location('/search?query=%s' % urllib.quote_plus(pattern))

        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()

    def get_video(self, _id):
        self.location(self.id2url(_id))
        return self.page.video

    def get_video_title(self, _id):
        self.location(self.id2url(_id))
        return self.page.video.title

    def get_video_url(self, _id):
        self.location(self.id2url(_id))
        return self.page.video.url
