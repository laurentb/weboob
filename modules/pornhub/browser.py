# -*- coding: utf-8 -*-

# Copyright(C) 2016 Roger Philibert
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

from .pages import IndexPage, VideoPage


__all__ = ['PornhubBrowser']


class PornhubBrowser(PagesBrowser):
    BASEURL = 'https://www.pornhub.com'

    index = URL(r'/$', IndexPage)
    search = URL(r'/video/search\?search=(?P<pattern>.+)\&page=(?P<pagenum>\d+)', IndexPage)
    video = URL(r'/view_video.php\?viewkey=(?P<id>.*)', VideoPage)

    @video.id2url
    def get_video(self, url, video=None):
        self.location(url)
        assert self.video.is_here()

        return self.page.get_video(video)

    def search_videos(self, pattern):
        self.search.go(pattern=pattern, pagenum=1)
        assert self.search.is_here()

        return self.page.iter_videos()

    def latest_videos(self):
        self.index.go()
        assert self.index.is_here()

        return self.page.iter_videos()
