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


import logging
import re
import urllib

from weboob.tools.browser import BaseBrowser, BrowserUnavailable
from weboob.tools.browser.decorators import check_domain, id2url
from weboob.tools.misc import iter_fields, to_unicode

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

    def fillobj(self, video, fields):
        # ignore the fields param: VideoPage.get_video() returns all the information
        self.location(YoujizzVideo.id2url(video.id))
        return self.page.get_video(video)

    @id2url(YoujizzVideo.id2url)
    def get_video(self, url):
        self.location(url)
        return self.page.get_video()

    @check_domain
    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()

    def iter_search_results(self, pattern):
        if not pattern:
            self.home()
        else:
            self.location('/search/%s-1.html' % (urllib.quote_plus(pattern)))
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()
