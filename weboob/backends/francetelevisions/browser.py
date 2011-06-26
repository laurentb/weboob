# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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

from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url

from .pages import IndexPage, VideoPage, MetaVideoPage
from .video import PluzzVideo


__all__ = ['PluzzBrowser']


class PluzzBrowser(BaseBrowser):
    DOMAIN = 'pluzz.fr'
    ENCODING = None
    PAGES = {r'http://[w\.]*pluzz.fr/?': IndexPage,
             r'http://[w\.]*pluzz.fr/recherche.html.*': IndexPage,
             r'http://[w\.]*pluzz.fr/[-\w]+/.*': IndexPage,
             r'http://[w\.]*pluzz.fr/((?!recherche).+)\.html': VideoPage,
             r'http://info\.francetelevisions\.fr/\?id-video=.*': MetaVideoPage,
            }

    @id2url(PluzzVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        assert self.is_on_page(VideoPage)

        metaurl = self.page.get_meta_url()
        id = self.page.get_id()
        self.location(metaurl)
        assert self.is_on_page(MetaVideoPage)

        return self.page.get_video(id, video)

    def iter_search_results(self, pattern):
        if not pattern:
            self.home()
        else:
            self.location(self.buildurl('recherche.html', q=pattern))

        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()
