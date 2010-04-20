# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz, Romain Bignon

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

import urllib
import re

from weboob.tools.browser import BaseBrowser
from weboob.tools.parsers.lxmlparser import LxmlHtmlParser

from .pages import VideoPage, ResultsPage

__all__ = ['YoutubeBrowser']

class YoutubeBrowser(BaseBrowser):
    PAGES = {'.*youtube\.com/watch\?v=(.+)': VideoPage,
             '.*youtube\.com/results\?.*': ResultsPage,
            }

    def iter_search_results(self, pattern, sortby):
        if not pattern:
            self.home()
        else:
            if sortby:
                sortby = '&search_sort=%s' % sortby
            self.location('http://www.youtube.com/results?search_type=videos&search_query=%s%s' % (urllib.quote_plus(pattern), sortby))

        assert self.is_on_page(ResultsPage)
        return self.page.iter_videos()

    def get_video(self, _id):
        if re.match('^\w+$', _id):
            url = 'http://www.youtube.com/watch?v=%s' % _id
        else:
            url = _id

        self.location(url)
        return self.page.video
