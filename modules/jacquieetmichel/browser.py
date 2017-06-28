# -*- coding: utf-8 -*-

# Copyright(C) 2013 Roger Philibert
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

from weboob.deprecated.browser import Browser
from weboob.deprecated.browser.decorators import id2url
from weboob.tools.compat import quote

from .video import JacquieEtMichelVideo
from .pages import VideoPage, ResultsPage


__all__ = ['JacquieEtMichelBrowser']


class JacquieEtMichelBrowser(Browser):
    DOMAIN = u'jacquieetmicheltv.net'
    ENCODING = None
    PAGES = {r'https?://.*jacquieetmicheltv.net/': ResultsPage,
             r'https?://.*jacquieetmicheltv.net/videolist/.*': ResultsPage,
             r'https?://.*jacquieetmicheltv.net/showvideo/(?P<id>\d+)/.*': VideoPage,
            }

    @id2url(JacquieEtMichelVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        assert self.is_on_page(VideoPage), 'Should be on video page.'
        return self.page.get_video(video)

    def search_videos(self, pattern):
        self.location('/videolist/searchmodevideo/query%s/' % (quote(pattern.encode('utf-8'))))
        assert self.is_on_page(ResultsPage)
        return self.page.iter_videos()

    def latest_videos(self):
        self.home()
        assert self.is_on_page(ResultsPage)
        return self.page.iter_videos()
