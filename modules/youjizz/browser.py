# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Roger Philibert
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


import urllib

from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url

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
        assert self.is_on_page(VideoPage), 'Should be on video page.'
        return self.page.get_video(video)

    def search_videos(self, pattern):
        self.location('/search/%s-1.html' % (urllib.quote_plus(pattern.encode('utf-8'))))
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()

    def latest_videos(self):
        self.home()
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()
