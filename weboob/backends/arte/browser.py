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

from .pages import IndexPage, VideoPage
from .video import ArteVideo


__all__ = ['ArteBrowser']


class ArteBrowser(BaseBrowser):
    DOMAIN = u'videos.arte.tv'
    ENCODING = None
    PAGES = {r'http://videos.arte.tv/fr/videos/arte7.*': IndexPage,
             r'http://videos.arte.tv/fr/do_search/videos/recherche.*': IndexPage,
             r'http://videos.arte.tv/fr/videos/(?P<id>.+)\.html': VideoPage
            }

    @id2url(ArteVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        return self.page.get_video(video)

    def home(self):
        self.location('http://videos.arte.tv/fr/videos/arte7')

    def iter_search_results(self, pattern):
        if not pattern:
            self.home()
        else:
            self.location(self.buildurl('/fr/do_search/videos/recherche', q=pattern))
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()
