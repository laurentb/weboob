# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser import PagesBrowser, URL
from weboob.capabilities.base import UserError

from .pages.index import IndexPage
from .pages.video import VideoPage


__all__ = ['YoupornBrowser']


class YoupornBrowser(PagesBrowser):
    BASEURL = 'https://www.youporn.com'

    home = URL('/$', IndexPage)
    search = URL('/search/\?query=(?P<query>.*)', IndexPage)
    video = URL('/watch/(?P<id>[0-9]+)/.*', VideoPage)

    def get_video(self, _id):
        self.video.go(id=_id)
        assert self.video.is_here()
        return self.page.get_video()

    def search_videos(self, pattern, sortby):
        if pattern == 'a' or pattern == 'i':
            raise UserError('this pattern is not supported');

        self.search.go(query=pattern)
        assert self.search.is_here()
        return self.page.iter_videos()

    def latest_videos(self):
        self.home.go()
        assert self.home.is_here()
        return self.page.iter_videos()
