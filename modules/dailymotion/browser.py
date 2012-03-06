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

from urllib import quote_plus

from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url

from .pages import IndexPage, VideoPage
from .video import DailymotionVideo


__all__ = ['DailymotionBrowser']


class DailymotionBrowser(BaseBrowser):
    DOMAIN = 'dailymotion.com'
    ENCODING = None
    PAGES = {r'http://[w\.]*dailymotion\.com/?': IndexPage,
             r'http://[w\.]*dailymotion\.com/(\w+/)?search/.*': IndexPage,
             r'http://[w\.]*dailymotion\.com/video/(?P<id>.+)': VideoPage,
            }

    @id2url(DailymotionVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        return self.page.get_video(video)

    def iter_search_results(self, pattern, sortby):
        if not pattern:
            self.home()
        else:
            pattern = pattern.replace('/', '').encode('utf-8')
            if sortby is None:
                url = '/search/%s/1' % quote_plus(pattern)
            else:
                url = '/%s/search/%s/1' % (sortby, quote_plus(pattern))
            self.location(url)

        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()
