# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Roger Philibert
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


from weboob.tools.browser2 import PagesBrowser, URL

from .pages.index import IndexPage
from .pages.video import VideoPage


__all__ = ['YoujizzBrowser']


class YoujizzBrowser(PagesBrowser):
    BASEURL = 'http://www.youjizz.com'

    index = URL(r'/?(index.php)?$',
                r'/page/\d+.html',
                IndexPage)
    search = URL(r'/search/(?P<pattern>.+)-(?P<pagenum>\d+).html', IndexPage)
    video = URL(r'/videos/(?P<id>.*).html', VideoPage)

    @video.id2url
    def get_video(self, url, video=None):
        self.location(url)
        assert self.video.is_here()

        return self.page.get_video(video)

    def search_videos(self, pattern):
        self.search.go(pattern=pattern, pagenum=1)
        assert self.search.is_here(pattern=pattern, pagenum=1)

        return self.page.iter_videos()

    def latest_videos(self):
        self.index.go()
        assert self.index.is_here()

        return self.page.iter_videos()
