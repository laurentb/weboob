# -*- coding: utf-8 -*-

# Copyright(C) 2015      P4ncake
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
from weboob.tools.compat import quote_plus

from .pages import SearchPage, PostPage


class VineBrowser(PagesBrowser):
    BASEURL = 'https://vine.co'

    search_page = URL(r'/api/posts/search/(?P<pattern>.*)',SearchPage)
    post_page = URL('r/api/timelines/posts/s/(?P<_id>.*)', PostPage)

    def search_videos(self, pattern):
        return self.search_page.go(pattern=quote_plus(pattern.encode('utf-8'))).iter_videos()

    def get_video(self, _id):
        return self.post_page.go(_id=_id).get_video()
