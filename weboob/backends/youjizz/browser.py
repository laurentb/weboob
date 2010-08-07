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


import urllib

from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import check_domain, id2url

from .pages.index import IndexPage
from .pages.video import VideoPage
from .video import YoujizzVideo


__all__ = ['YoujizzBrowser']


class YoujizzBrowser(BaseBrowser):
    DOMAIN = 'youjizz.com'
    ENCODING = None
    PAGES = {r'http://.*youjizz\.com/?': IndexPage,
             r'http://.*youjizz\.com/index.php': IndexPage,
             r'http://.*youjizz\.com/search/(?P<pattern>.+)\.html': IndexPage,
             r'http://.*youjizz\.com/videos/(?P<id>.+)\.html': VideoPage,
            }

    @id2url(YoujizzVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        return self.page.get_video(video)

    def iter_search_results(self, pattern):
        if not pattern:
            self.home()
        else:
            self.location('/search/%s-1.html' % (urllib.quote_plus(pattern)))
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()
