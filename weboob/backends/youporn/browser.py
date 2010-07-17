# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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


from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url

from .pages.index import IndexPage
from .pages.video import VideoPage
from .video import YoupornVideo


__all__ = ['YoupornBrowser']


class YoupornBrowser(BaseBrowser):
    DOMAIN = 'youporn.com'
    ENCODING = None
    PAGES = {r'http://[w\.]*youporn\.com/?': IndexPage,
             r'http://[w\.]*youporn\.com/search.*': IndexPage,
             r'http://[w\.]*youporn\.com/watch/(?P<id>.+)': VideoPage,
             r'http://[w\.]*youporngay\.com:80/watch/(?P<id>.+)': VideoPage,
            }

    @id2url(YoupornVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        return self.page.get_video(video)

    def iter_search_results(self, pattern, sortby):
        if not pattern:
            self.home()
        else:
            self.location(self.buildurl('/search/%s' % sortby, query=pattern))
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()
